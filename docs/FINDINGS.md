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
