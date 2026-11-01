# Findings — verified API shapes

Build only on shapes recorded here. P0 re-runs a smoke test for each and appends what it sees. Exa is not verified yet.

## Sarvam chat (`sarvamai` 0.1.41, model `sarvam-105b`)

- Call: `SarvamAI(api_subscription_key=KEY).chat.completions(model="sarvam-105b", messages=..., tools=..., tool_choice="auto", reasoning_effort=None, max_tokens=400)`.
- Response: `choices[0].message` has `content, refusal, reasoning_content, role, tool_calls`. `finish_reason == "tool_calls"` when a tool is wanted. A tool call looks like `{"id": "chatcmpl-tool-…", "type": "function", "function": {"name": "set_volume", "arguments": "{\"action\": \"down\"}"}}`; `arguments` is a JSON string.
- Multi-turn native tool calling works: append the assistant message, then `{"role": "tool", "tool_call_id": id, "content": ...}`, and call again.
- `content` is `null` whenever `tool_calls` is present.
- No parallel tool calls seen. The model sometimes chains shell steps into one command with `&&`, so the gate must score every part.
- `reasoning_effort=None` gives 0 reasoning tokens. `reasoning_effort="none"` returns HTTP 400.
- Bad key: `sarvamai.errors.forbidden_error.ForbiddenError`, status 403.
- Latency: 280–1,000 ms per turn. Use a 12 s per-call timeout with one retry.
- Structured output also works: `response_format={"type": "json_schema", "json_schema": {"name": ..., "strict": True, "schema": ...}}`.

## Sarvam realtime STT

- Connect: `AsyncSarvamAI(api_subscription_key=KEY).speech_to_text_realtime_streaming.connect(language_code="auto", model="saaras:v3-realtime", stream_type="fast")`.
- Send: `send_realtime_audio_input(RealtimeAudioInput(audio=<base64 of 16 kHz mono int16>))`, 3,200-byte chunks (100 ms). End: `send_realtime_end(RealtimeEnd())`.
- Events in order: `session.begin`, `vad.speech_start`, many `transcript.partial` (`text`, `language`), `vad.speech_end`, `transcript.final` (`text`, `language`, `language_confidence`), `session.end`.
- For push-to-talk use `endpointing="manual"`: on release send the end message; `transcript.final` arrives 195–341 ms later.
- Partials are often wrong until the end; show them only as live feedback.
- `language_code="auto"` tags Hinglish as `en-IN` with low confidence (about 0.63). Trust the detected language only at ≥ 0.8.
- Close codes: 1003 rate limit or bad key, 1008 inactivity, 1011 server error, 4000 bad parameter.

## Sarvam TTS

- Call: `SarvamAI(...).text_to_speech.convert(text=..., language_code="hi-IN", model="bulbul:v4-flash", speaker="ratan_hi_social", speech_sample_rate=24000, output_audio_codec="wav")`.
- Response: `audios` is a list with one base64 WAV.
- Latency: about 565 ms for a short line, 2.6–3.3 s for a 25-word line.
- v4 speakers are tied to one language: `ratan_hi_social` only works with `hi-IN`. Send every line as `hi-IN`, including English sentences.
- Codecs: wav, mp3, aac, flac, linear16. Max 2,500 characters per request.

## Laya (`laya` 0.4.18, model in `models/laya/`)

- Load: `os.environ["USE_TF"] = "0"; import laya; agent = laya.Agent("models/laya")`. Warm load 6–9 s. `laya.Agent(path)` loads exactly this one model.
- Call: `agent.predict(state, {"risk_tier": RISK_TIER, "verify_call": VERIFY_CALL})`, both questions in one call. First call about 3.7 s (warm-up), then p50 about 50 ms.
- Result shape:

  ```json
  {"answers": {"risk_tier": {"type": "choice", "choice": "T1",
     "probabilities": {"T0": 0.11, "T1": 0.69, "T2": 0.10, "T3": 0.09},
     "confidence": 0.31, "answer_confidence": 0.69}}, "usage": {...}}
  ```

- The answer probability is `answer_confidence`, equal to the chosen option's entry in `probabilities`. `confidence` is a different, lower score; do not gate on it.
- The model's own temperatures are already applied inside `laya`.
- Accuracy on held-out rows: risk_tier 0.985, verify_call 0.969, confirm_reply 0.927. Calibration error 0.008, 0.019, 0.051.
- Weakness: it rated credential reads (`security find-generic-password`, `Get-Credential`) and `curl … | sh` as low risk. Keep the regex tier as a floor.
- Non-Latin replies to the confirm question are unreliable; use the keyword lexicon for them.

## Codex CLI (version 0.153.4, from `codex --help`; P0 must run it live)

- Non-interactive: `codex exec [OPTIONS] "<prompt>"`.
- Useful flags: `-C <dir>`, `-s <sandbox mode>`, `-m <model>`, `--skip-git-repo-check`, `--ephemeral`, `--json` (JSONL events on stdout), `-o <file>` (last message).
- Never use `--dangerously-bypass-approvals-and-sandbox`.
- Login with API credits: `printenv OPENAI_API_KEY | codex login --with-api-key` (a human step). Check with `codex login status`.

## Exa

Not verified. P0: read the `exa-py` docs, make one search, and record the call and response shape here before building `web_search`.

## P0 live verification: 2026-11-01

Run with `.venv/bin/python scripts/smoke.py <sarvam|laya|codex|exa|tts|stt-shape>`.
All probes are gated before calling an integration. Network probes need network access.

- Sarvam 0.1.41: actual `choices[0].message` was
  `{"role":"assistant","tool_calls":[{"type":"function","function":{"name":"set_volume","arguments":"{\"action\": \"decrease\"}"}}],"content":null}`.
  The deliberately minimal smoke schema did not enumerate actions; runtime MUST enumerate
  `up/down/mute/unmute/set` and validate them. `finish_reason="tool_calls"`, reasoning tokens 0.
- Laya 0.4.18 loaded the existing model unchanged in **16.488 s**. First inference 432 ms,
  second 204 ms on this host (slower than the original estimates).
  `lower volume / set_volume {"action":"down"}` returned risk probabilities
  `{T0:0.0055,T1:0.9835,T2:0.0055,T3:0.0055}`, verify execute **0.9872**.
  `delete all files / run_command {"command":"rm -rf ."}` returned T3 **0.9819**,
  verify execute **0.9851**. Read `probabilities`, not `confidence`.
- Codex CLI **0.153.4**, existing ChatGPT login. Default configured `gpt-6.1-sol` was
  rejected with HTTP 400 `model_not_found` for this account. Local model cache advertised
  `gpt-5.6-terra`; explicitly using `-m gpt-5.6-terra` completed successfully, exit **0**.
  Actual JSONL types: `thread.started`, `turn.started`, `item.started/completed` with
  `command_execution`, `file_change`, `agent_message`, then `turn.completed`.
  Created `sandbox/p0-smoke/index.html`: `<h1>Billu says hello</h1>`.
  Runtime uses this verified model, overridable by `CODEX_MODEL` in `.env`.
  CLI flags confirmed with installed `codex exec --help` and
  https://developers.openai.com/codex/cli/reference .
- Exa **2.27.0**: installed SDK deprecates `search_and_contents`. Verified current call:
  `Exa(api_key=KEY).search("Delhi cutting chai", num_results=3)`.
  `response.results` contains objects with `.title`, `.url`, `.text`.
  Actual first result: title `Delhi Chai Cafe Menu | Premium Tea & Snacks India`,
  URL `https://delhichaicafe.com/menu/`, text beginning `Delhi Chai Cafe Menu | Best Chai`.
  Three populated results returned. Runtime caps extracted text and labels it web data.
- TTS: verified exact recorded convert arguments, response had **1** audio,
  base64 length **102460**. Audio bytes deliberately omitted from logs.
- STT: installed SDK connect accepts `endpointing="manual"`, `encoding="linear16"`,
  `sample_rate="16000"`. `RealtimeAudioInput` fields: `event,audio`;
  `RealtimeEnd` fields: `event`. Live microphone round-trip is deferred to P4.

## P3 real background job

`scripts/smoke_code.py` ran the real gated `write_code`, using the verified CLI model
and its existing login. It returned `job started` immediately, then completed in
**65.96 seconds**, created `sandbox/chai-probe-10b8956c/index.html`, and ran the
fixed `open index.html` follow-up through a fresh policy decision and GateToken.
No volume action or speech service was invoked. `scripts/check_app.mjs` exercised
the generated app's actual JS handlers in an isolated logic test: plus, minus,
reset and the zero lower bound all passed. This is not a browser/pointer test.
Browser verification remains unavailable: browser host unavailable, Safari native
access not approved. The server, API/event flow and app CSP are covered in tests.

## P4 corrected realtime manual protocol (live verified)

The earlier STT manual-end note was incomplete. Sending audio followed only by
`RealtimeEnd()` produced `session.end` with `total_utterances:0` and no final.
The working manual sequence is:

1. Connect with `endpointing="manual", encoding="linear16", sample_rate="16000"`.
2. `await socket.send_realtime_speech_start(RealtimeSpeechStart())`.
3. Send 3,200-byte, base64 PCM frames through `send_realtime_audio_input`.
4. `await socket.send_realtime_speech_end(RealtimeSpeechEnd())` on PTT release.
5. Receive `transcript.final`, then send `RealtimeEnd()` to close the session.

Verified with `python -m scripts.smoke_stt`, synthesizing Hindi speech in memory
without accessing the microphone. Actual final:
`{"event":"transcript.final","utterance_idx":0,"text":"Billu, aawaz kam karo","language":"en-IN","language_confidence":0.61}`.
Many `transcript.partial` events preceded it, with `.text` and `.language` fields.
SDK socket supports `async for event in socket`; events have `.model_dump()`.
Use Hindi/Hinglish UI copy when language confidence is below 0.8.
Official reference: https://docs.sarvam.ai/api/api-guides-tutorials/speech-to-text/realtime-streaming .

The full runtime pipeline also passed via `python -m scripts.smoke_voice_pipeline`:
real synthesized Hindi -> runtime `VoiceSession` -> real Sarvam tool call -> real
Laya -> policy/GateToken -> **fake** volume 50 to 40 -> real Hindi TTS WAV.
Recognized final `aawaz kam karo`; called `set_volume {"action":"down"}`.
Laya returned T1 **0.9784**, verify `wrong_tool` **0.4309** (below the 0.70 veto
threshold, so policy correctly allowed). First runtime inference took **1156 ms**;
this host must not be presented as a verified 50 ms machine. Reply WAV: **96044** bytes.
No microphone or real volume was accessed. UI/browser microphone permission and
actual loudspeaker playback remain unverified because computer use is unavailable.
The JS resampler passed constant-signal, 100 ms frame size and final-padding checks
at both 44.1 kHz and 48 kHz input rates (`node scripts/check_pcm.mjs`).

## P5 rehearsal and final verification

- `python -m scripts.seed_demo`: created three synthetic 2024-dated PNGs under
  `sandbox/screenshots/`, with `.Trash/` also inside sandbox. Seeding executes via
  `policy_gate`, a matching GateToken and an operator-only deterministic write_code
  handler. It preserves existing files. No actual desktop screenshots are captured.
- `python -m scripts.rehearse`: **5/5 beats, three consecutive passes**, plus unmute.
  These are accelerated fake rehearsals (about 1.3 s each), not three physical
  90-second voice performances. No desktop or external service calls occur.
- `python -m scripts.smoke_shell`: real confined mkdir, echo redirect, explicitly
  confirmed move and read passed inside a fresh `sandbox/shell-probe-*` folder.
- Final `pytest -q`: **71 passed**. `ruff check .`: clean. All four UI JS modules
  parsed with `node --check`; PCM checks passed at 44.1 and 48 kHz.
- HTML audit: no duplicate IDs, no missing JS control targets, no external asset URLs.
- Shell deliberately uses zsh `-f -c` instead of login `-lc`, so user startup files
  cannot run commands or write outside sandbox. Model text is parsed, confined and
  safely reconstructed before reaching zsh. No shell=True is used.
- Laya now warms one inference before setting readiness. The weights and exact
  question/state templates remain unchanged. Keyword fallback operates during warm-up.
- Full design-law review and verification limits: `docs/UI_AUDIT.md`.

## Electron desktop integration

User requested Electron with native permission onboarding and audible replies.
Official APIs reviewed before implementation:
- https://www.electronjs.org/docs/latest/api/system-preferences :
  `getMediaAccessStatus('microphone')`, `askForMediaAccess('microphone')` returns
  Promise<boolean>; macOS requires NSMicrophoneUsageDescription in Info.plist.
  Previously denied mic permission needs System Settings and app restart.
  `isTrustedAccessibilityClient(true)` triggers the native accessibility prompt.
- https://www.electronjs.org/docs/latest/api/session : permission check/request
  handlers restrict media to the trusted main app and audio only.
- https://www.electronjs.org/docs/latest/api/browser-window : sandbox/context
  isolation/no Node in renderer; `autoplayPolicy='no-user-gesture-required'`.
Electron and packager registry probes: electron 45.2.1, @electron/packager 20.3.0.
The desktop app uses an owned Python backend on a kernel-assigned loopback port,
with an ephemeral in-memory authorization token. No API key enters the renderer.

Electron live probe now verified **45.2.1**. `askForMediaAccess` and session
permission handler are functions. Read-only host status was microphone denied,
Accessibility false; the probe did not change either permission. The packaged
Info.plist contains the microphone purpose string.

`npm run smoke:electron` completed actual Electron Web Audio PCM playback and
SpeechSynthesis output. The full app also passed `npm run start:fake -- --smoke`:
authenticated Python backend ready, renderer audio WebSocket connected, system
speech receipt `status:"completed"`. This tests normal renderer startup without
synthetic clicks or bypassing microphone permissions. The browser/native computer
use tool still refused Electron access, so actual pointer/pixel checks remain open.

The launching environment inherited ELECTRON_RUN_AS_NODE, which initially made
Electron behave as Node. `desktop/launch.cjs` now removes it before starting the
runtime. No global environment or existing application is modified.

Full Electron **live Sarvam** playback passed as well:
`npm start -- --smoke` -> backend true, rendererAudioConnected true,
voice provider `sarvam`, status `completed`. The same normal startup and audio
code is used; smoke mode only skips native permission prompts and quits after
observing a real playback receipt. It does not fabricate audio or grant OS access.

Desktop tests: **7 passed**; Python tests: **76 passed**. npm audit: **0**
vulnerabilities after pinning patched glob/minimatch build dependencies.
The built macOS app has bundle ID `dev.hacksmith.catbot`, a real Billu icon,
and the microphone usage description. It is a local checkout-backed desktop app,
not a portable Python/Torch installer. It starts/stops the sidecar automatically.

The packaged `Catbot.app` also passed its own live `--smoke` run with provider
`sarvam` and completion status. The app icon bytes match the generated Billu ICNS.
Permission sequencing has a regression test: previously denied microphone access
stays on that settings step; Accessibility is requested after microphone grant,
so one settings pane cannot immediately replace the other.

## P7 voice-input RuntimeError fix

Live reproduction on 2026-11-01:
- Normal synthesized Hindi still returned a final transcript successfully.
- Manual `speech_start` followed immediately by `speech_end` with **zero audio
  frames** returned `{"event":"error","code":"transcriber_error","message":
  "Transcription failed for utterance 0.","is_fatal":false}`.
- One and ten all-zero frames returned an empty `transcript.final`.
The old runtime collapsed provider error and early session end into RuntimeError.
This reproduces the reported message; it does not establish which recording or
microphone state the user had on their physical machine.

The runtime now waits for nonzero PCM before connecting to Sarvam, preserving a
200 ms pre-roll. Empty presses and digital-silence captures produce local,
actionable messages without opening a service connection. Real speech remains
streamed immediately, and only final transcripts can start actions. Structured
provider errors distinguish authentication, quota, transcription and connection
failures. Diagnostics record only safe code, duration and peak, never audio or
raw provider payloads. Voice errors stop recording and close the capture graph.

Capture requests use a generation counter so a delayed permission result from
an earlier press cannot replace or stop the next microphone stream. Releasing
while Web Audio unlocks cannot start the microphone later. Processor failure and
microphone disconnection stop capture explicitly.

The full live `scripts.smoke_voice_pipeline` passed after the fix: real STT,
Sarvam chat, Laya and TTS, with fake volume 40 and a 180524-byte reply WAV. No
physical microphone or real volume action was used by the probe.


## Talk control and denied microphone access

The session media handler called the same permission helper as the explicit
setup buttons. With a denied microphone, each getUserMedia attempt consequently
opened the macOS microphone Settings pane. Capture requests now allow the initial
OS prompt but never navigate to Settings; the explicit Enable microphone action
retains that navigation. A regression check repeats denied capture requests and
asserts there is no navigation before the explicit setup request. Restarting can
apply a grant made in Settings, but cannot itself grant microphone access.


## Simple mode initialization fix

The coding panel had class `code` but no ID `code`. The mode controller requested
that ID while preparing the controls to move, causing a null-element exception
before the click listener was registered. The panel now has the expected ID.
The regression test constructs its available elements from the actual HTML IDs,
rather than inventing any element requested by the test. It failed before this
fix and passes after it. Mode initialization failures also surface a visible
message instead of leaving a silently inactive control. Rebuilding alone did
not resolve the original missing-element error.


## Space activated the view button instead of recording

The user reported that holding Space changed simple/dashboard mode. The global
shortcut excluded all buttons, allowing the focused view toggle's native Space
click. The input controller now captures Space keydown and keyup outside text
fields/dialogs and cancels the native activation, while keeping Enter for regular
button activation. It displays microphone startup/cancellation immediately and
handles pointer-capture failure without skipping recording. Regression tests
exercise both key events with the mode button focused. Actual OS microphone
permission and physical capture are still separate from this verified input
routing fix.


## P14 screenshot capability and demo validation

Verified native shapes before use:
- `/usr/sbin/screencapture -h` prints usage (and exits nonzero because `-h` is
  not an option). The installed help documents `-x` silent, `-m` main monitor,
  `-t` format and a destination file. The tool uses the fixed argv
  `/usr/sbin/screencapture -x -m -t png <sandbox/captures/uuid.png>`.
- Installed Electron 45.2.1 declarations accept `getMediaAccessStatus('screen')`.
  The packaged application's diagnostic response was microphone `granted`,
  screen `denied`, Accessibility `granted`.
- Primary references: https://www.electronjs.org/docs/latest/api/system-preferences
  and https://www.electronjs.org/docs/latest/api/desktop-capturer . Screen
  capture requires macOS consent. `askForMediaAccess` does not accept `screen`;
  the explicit screenshot setup action opens the Screen Recording Settings pane.
- Apple SDK CGWindow.h also declares `bool CGPreflightScreenCaptureAccess(void)`
  and `bool CGRequestScreenCaptureAccess(void)`. These were inspected for
  diagnostics research; the implementation does not use them.

`take_screenshot` is a registered, T1 local tool with an empty, closed schema.
It needs an issued single-use GateToken, reserves a unique confined output path,
checks the PNG signature/dimensions, removes incomplete files and returns no image
bytes to the model. Previews require the same desktop token; fake mode exposes
no real captures. Screenshots use a separate captures folder from the seeded old
screenshots so the trash demo does not accidentally target new screen captures.

Live testing found that the foreground model sometimes kept calling tools after
a background coding job had successfully started. Successful write_code now ends
the foreground request, while the existing background job owns progress and
completion. Successful/failed screenshots similarly finish after their one result.
A regression brain that repeatedly proposes write_code confirms one foreground
execution and a successful background handoff.

Validation on 2026-11-01:
- 94 Python tests and 18 Electron tests pass; Ruff is clean.
- All five demo beats pass three accelerated rehearsals, plus unmute and fake
  screenshot on each run.
- Real Sarvam/Laya/TTS rehearsal passes app start, confirmed trash, hard destructive
  denial, pet-paid mute, unmute and screenshot routing. Eleven WAV replies were
  produced. Desktop/code actions in this rehearsal are explicitly faked.
- Separate real Codex build completed in 60.37s at
  sandbox/chai-probe-0e0b08bb/index.html; generated plus/minus/reset/lower-bound
  handlers pass a logic-only check. The checker now recognizes actual increase/
  decrease IDs and document-level shortcut registration instead of assuming IDs.
- Real synthesized audio -> Sarvam STT -> Sarvam chat/Laya -> fake volume 40 ->
  real TTS passed, with a 130604-byte WAV reply.
- The user's real microphone request was transcribed as `Screenshot`; Laya/policy
  allowed take_screenshot, actual capture failed with a permission explanation,
  and the task ended as screenshot_failed instead of looping. At that point the
  packaged app reported screen permission denied. Real PNG capture awaits the
  human enabling Catbot's screen permission and relaunching.


## P15 packaged signing identity and permission recheck

After the human enabled Catbot and a restart, screen status still reported denied
and a gated live capture failed. Inspection found that the original packager
output retained the Electron linker signature: Identifier=Electron, Info.plist
not bound, Sealed Resources=none. `codesign --verify --deep --strict` failed with
"code has no resources but signature indicates they must be present".

The packager now uses its installed @electron/osx-sign integration with a local
ad-hoc identity, identityValidation=false, preAutoEntitlements=false,
preEmbedProvisioningProfile=false, and per-file hardenedRuntime=false with no
timestamp. No developer certificate or notarization was used. After packaging,
strict verification succeeds, the identifier is dev.hacksmith.catbot, Info.plist
is bound and resources are sealed. Packaging now verifies these properties and
fails if the identity is wrong. Official reference:
https://packages.electronjs.org/packager/v20.2.0/interfaces/Options.html#osxsign .

Launch the packaged app through Finder or Launch Services (`env -u
ELECTRON_RUN_AS_NODE open -a <Catbot.app>`), rather than directly executing the
inner binary from an IDE. The IDE-provided ELECTRON_RUN_AS_NODE also affected the
first Launch Services diagnostic attempt; removing it restores normal startup.

The corrected identity is treated as a new app by macOS: its initial diagnostics
reported microphone not-determined, screen denied, Accessibility not-granted.
The old permission entry must be replaced with the rebuilt copy and enabled;
this is an OS grant that the agent cannot supply. Real capture retesting is
pending that regrant. No capture success has been claimed.


### Native capture transport and final permission test

To remove child-process permission attribution ambiguity, Electron now owns
screen capture via `desktopCapturer.getSources` with screen-only sources,
main-display dimensions, no window icons, and a 12-second deadline. A private
loopback HTTP transport accepts only POST /capture with a distinct random bearer
token supplied to the Python child in memory. The gated screenshot tool is its
only application caller; the renderer receives neither endpoint nor token.
Requests with bodies, arbitrary paths, missing credentials, or fake mode are
rejected. Fake mode never calls desktopCapturer. The Python receiver accepts only
a loopback /capture endpoint and limits PNG transfers to 50 MB before storing the
unique sandbox file. The shell fallback remains only for standalone macOS use.
Tokens are hidden from Settings repr and added to event redaction.

Unit checks pass for the native transport's authentication, fixed display/source
options, actual HTTP status behavior, fake-mode isolation and Python transport
confinement. Current totals: 95 Python + 19 Electron tests; Ruff clean. The signed
bundle starts through Launch Services and passes deep strict codesign verification.
Packager returns output directories, so post-sign verification resolves their
Catbot.app child rather than checking the parent directory.

After the human re-enabled the final native build and macOS reopened it, a normal
Sarvam/Laya-gated screenshot still failed. A separate gated transport diagnostic
confirmed native HTTP 403 application/json with error=screen_capture_failed,
ruling out wrong credentials/malformed request as the cause. No PNG was produced.
Screen status continues to be denied. The current local ad-hoc designated
requirement is a code hash; no valid Developer ID or Apple Development signing
identity is installed. This is diagnostic context, not proof that a Developer ID
would resolve the permission issue. No bypass or false permission status was added.

Native System Settings inspection was refused with "Computer Use permissions are
not granted". Both relevant TCC databases were unavailable for read-only queries.
The next diagnostic input needed is a human screenshot of Catbot's row in Screen
& System Audio Recording. The final build is frozen so further code signing does
not invalidate the permission while that state is checked. Real capture is still
unverified and is not reported as working.


## P16 real capture verified after targeted TCC repair

Computer Use became available after the human enabled it. Direct System Settings
inspection showed Catbot enabled for Screen & System Audio Recording. Its Show
in Finder action resolved to this repository's dist/Catbot-darwin-arm64 folder,
ruling out a grant to a different installed copy.

The macOS privacy logs exposed the exact mismatch: TCC checked
`dev.hacksmith.catbot` against the old Electron cdhash
`2cc11dd82a0b0b85d58d5eddadadd3690850195a` and returned `-67050`.
The unchanged final native bundle's designated requirement was instead
`a2e80821de38d407abeea9d0b12bbc9da6e6549e`.
The enabled toggle alone therefore did not represent a valid grant for that code.

With explicit human approval, ran only
`tccutil reset ScreenCapture dev.hacksmith.catbot` (confirmed successful), then
used System Settings' Add picker to select the unchanged final bundle. The human
completed the required Touch ID authentication. Accepted Quit & Reopen. No other
app's grant was changed, and no binary was rebuilt or re-signed during this repair.
Catbot's own UI then reported Screen capture: Ready.

Submitted `Billu, take a screenshot of the main screen` using the real Catbot
input through native UI. The normal Sarvam/Laya/policy path allowed the call,
then the tool saved sandbox/captures/535ec34fe7d349a1bf7f85c8ef655bdd.png.
The authenticated View screenshot link opened a real 3024x1964 PNG preview.
Visual inspection confirmed actual desktop windows, including Catbot, rather
than wallpaper-only or a synthetic image. This completes the previously blocked
real-capture verification. The private screenshot remains ignored by git.

The current newly signed app's UI still reports microphone and Accessibility as
needing permission; only its screen grant was repaired in this operation. The
human can restore those grants through the existing setup controls. Earlier live
microphone evidence predates the signing identity repair. No new physical mic
success is claimed for this identity.
