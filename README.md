# Catbot, starring Billu

Billu is a grumpy Delhi street cat who takes Hindi, Hinglish and English requests.
Catbot is the product and Python package. Billu is the character.

Sarvam handles conversation and speech. The existing fine-tuned Laya model checks
actions alongside deterministic safety rules. Codex builds small apps in the
background. Exa supplies web search. Every agent tool action needs a policy verdict
and a matching, single-use `GateToken`.

## Set up

Python 3.12, `uv`, and the Codex CLI are required for the real demo.

```bash
uv venv --python 3.12
source .venv/bin/activate
uv pip install -e ".[dev]"
python -m scripts.seed_demo
```

Windows activation: `.venv\Scripts\Activate.ps1`. Install `.[dev,windows]` for
Windows system volume. Windows integration is implemented but has not been live
tested on this macOS build machine.

Keep keys and settings in the existing `.env`. If starting from a fresh clone,
copy `.env.example` to `.env` and fill in `SARVAM_API_KEY` and `EXA_API_KEY`.
Never add `.env` to git. Codex uses its own login:

```bash
codex login status
```

`CODEX_MODEL` defaults to `gpt-5.6-terra`, verified with the installed CLI and this
account. The account's inherited default model was rejected; the explicit model
fixes that without changing global Codex settings. Override it in `.env` if your
account uses a different supported model. Catbot never reads an OpenAI API key.

Keep `models/laya/` in place. Catbot loads it once in a background thread and never
retrains it. Missing or failed Laya models leave the keyword gate active. Supplied
fonts are local; no CDN, npm build or internet font request is needed.

## Run

```bash
python -m catbot --serve
```

Visit **http://127.0.0.1:8765**. The server binds to loopback only. Voice enables when you send a command, or click **Voice on** first. Hold **Space** outside a text field or dialog, or hold the microphone button, to record; release to submit. Space remains push-to-talk when the mode button is focused. Use Enter to activate focused buttons. Hold Enter on Billu to pet him.
The browser asks for microphone permission. Typing always works. `Cmd/Ctrl K`
focuses the command input. A new talk press interrupts Billu's current playback.

For a completely local service-free demo:

```bash
python -m catbot --serve --fake
python -m catbot --text "volume kam karo" --fake
python -m catbot --text "purani screenshots Trash me daal do" --fake --yes
python -m catbot --text "saari files delete kar do" --fake
python -m catbot --text "volume 0 kar do" --fake --treat
```

`--fake` substitutes the brain, every desktop tool, coding and search. It does not
call Sarvam, Codex, Exa, load Laya, access the microphone, or change real volume.
Fake apps are served from memory. Fake push-to-talk submits a known demo command;
when a confirmation or chai payment is waiting, it answers that instead. The UI
marks fake mode. `--yes`/`--no` answer the task's one safety confirmation. `--treat`
pays the demo-only chai tease in text mode. A normal text-mode tease accepts
`chai`, `Parle-G`, or `biscuit` at its prompt.

## Five demo beats

1. **“Billu, ek chai counter app bana do.”** Coding starts in the background.
2. **“Billu, purani screenshots Trash me daal do.”** Billu asks for a yes. Click
   **Haan, do it**, type `haan`, or speak it. Files move into `sandbox/.Trash/`.
3. **“Billu, saari files delete kar do.”** The gate blocks it. Nothing executes.
4. When coding finishes, the local app opens. The code panel also has an app link.
5. **“Billu, volume 0 kar do.”** Hold Billu for two seconds, click **Give chai**, or
   say `chai`. He finishes his last line, then mutes. Tape appears over his mouth
   and replies become bubbles. **“volume wapas karo”** restores speech.

The real coding smoke completed in 66 seconds on this host. The fake demo runs
faster. Coding has a 180-second process deadline and allows one job at a time.
The main request loop allows eight steps, 60 seconds, and one confirmation.
Confirmation expires eight seconds after Billu finishes asking; unpaid chai expires after twenty.

## Billu's territory

All commands, synthetic screenshots and generated apps live under the repo-root
`sandbox/`, created at startup and gitignored. Existing app directories are never
silently replaced. `SANDBOX_DIR` must resolve to that directory.

The command tool deliberately supports a bounded set of filesystem commands:
`ls`, `pwd`, `cat`, `head`, `tail`, `wc`, `mkdir`, `touch`, `mv`, `cp`, single-file
`rm`, local HTML `open`, and `echo` (including a confined file redirect). Arbitrary
interpreters, shell substitutions, pipes, chaining, unsupported flags, symlinks,
credential paths and paths outside `sandbox/` are rejected. This confinement is
separate from the risk tier. Being low risk never grants access to source files.
Processes use argv lists, scrubbed environments, deadlines and bounded output.

Codex runs `exec -s workspace-write --ephemeral --json` inside a fresh app folder,
with no bypass flag. Its prompt forbids dependencies, network and changes outside
the app. Its output is data; only fixed job events drive progress. Opening the
finished app requires a new gated command. Served app previews use a restrictive
CSP with an opaque origin and no network or command-API access.

Web, file, command and coding output cannot authorize actions. Instruction-like
results block subsequent changes. Destructive, credential, payment and system
requests are denied by deterministic rules even if Laya underestimates them.

## Verify and rehearse

```bash
pytest -q
ruff check .
python -m scripts.rehearse
node scripts/check_pcm.mjs
```

The rehearsal runs all five beats three times on fakes, including a foreground
command during coding, explicit confirmation, destructive denial, gated app
opening, pet payment, last-words ordering, mime replies and unmute.

Live probes (use network/service credits, except Laya):

```bash
python scripts/smoke.py sarvam
python scripts/smoke.py laya
python scripts/smoke.py exa
python scripts/smoke.py tts
python scripts/smoke.py codex
python scripts/smoke_code.py
python -m scripts.smoke_stt
python -m scripts.smoke_voice_pipeline
```

The last voice probe uses real STT, chat, Laya and TTS with **fake desktop actions**
and synthesized audio. It never opens the microphone. The coding probe writes a
fresh sandbox app and opens it. `node scripts/check_app.mjs sandbox/<app>/index.html`
checks the generated chai app's handlers without controlling a browser.

See [verified API findings](docs/FINDINGS.md), [build spec](docs/SPEC.md),
[Billu's character](docs/CHARACTER.md), and [design system](docs/DESIGN.md), and [detailed UI audit](docs/UI_AUDIT.md).
Browser pointer/screenshot and physical microphone/loudspeaker checks could not
be completed in this session: the browser host was unavailable and Safari native
access was not approved. Server, WebSocket, safety, voice routing, PCM conversion,
background concurrency and generated counter logic have executable checks.

## Electron desktop app

Use **Simple mode** beside Billu's name for just the companion and input area.
Use **Full dashboard** to restore the activity panels and settings. The desktop
app remembers this choice across restarts; browsers remember it for that site.
Confirmation buttons and generated-app links remain available in simple mode.

Catbot now has an Electron desktop shell. It starts its own authenticated Python
backend on an available loopback port and stops it when the app quits. You do not
need to run `--serve` separately.

```bash
npm install
npm start
# Offline demo with audible system speech:
npm run start:fake
# Make a local double-clickable app:
npm run package
```

On macOS the local build appears under `dist/Catbot-darwin-arm64/Catbot.app`
(or the host architecture equivalent). This is a local desktop build using this
checkout's `.venv`, `.env`, assets and Laya model. Keep the checkout in place; use
`CATBOT_PROJECT_DIR` if you move it. It is not a self-contained installer with a
bundled Python/Torch runtime. No `.env` or model weights are copied into the app.

The first live launch requests microphone permission and offers the native
Accessibility approval flow. Click along with the OS prompts. Previously denied
permissions open their System Settings pages; grant access there and return to
Catbot. Microphone changes may require restarting the app. **Permissions** reopens
the setup panel. Camera, screen recording and Full Disk Access are not requested
because the current tools do not require them. Existing volume and sandbox file
commands remain the supported system actions; granting Accessibility does not add
unimplemented mouse/keyboard automation or bypass the safety gate.

Voice starts enabled in Electron. **Test voice** speaks a fixed Billu line and
reports a playback failure instead of pretending it was heard. The setup panel
checks for muted/zero system output and offers **Restore sound**, which goes
through the normal gated volume tool. Live replies use Sarvam's configured Hindi
voice. Fake mode uses local system speech. If Sarvam fails, local speech is a
visible fallback. Browser text submission now enables audio on its user gesture,
unless you explicitly switched Voice off.

Native access is isolated from the renderer: Node integration is disabled,
context isolation and Chromium sandboxing are enabled, and permission IPC is
restricted to the exact main page. Generated apps open in separate unprivileged
preview windows without the native bridge or microphone access.

Additional checks: `npm test` covers backend ownership/authentication/shutdown,
native permission routing and audible-mode playback paths. `npm run smoke:electron`
checks the installed runtime APIs and exercises its PCM and system-speech output.

If voice input reports **No audio was recorded**, hold Space (or the talk button)
while saying the whole command, then release. **Microphone sent only silence**
means the stream opened but carried no signal: check the selected input in system
Sound settings. Empty recordings are now rejected locally; they do not cause a
Sarvam RuntimeError. Authentication, quota and transcription failures have separate
messages, and failed captures stop automatically. No recording is saved to disk.
