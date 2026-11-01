# Catbot: one-minute demo

Catbot is an Electron desktop agent starring Billu, a grumpy Delhi street cat.
Speak or type in Hindi, Hinglish or English: Sarvam handles conversation and voice,
the pretrained local Laya model evaluates proposed actions, and a deterministic
policy gate controls execution. Billu takes screenshots and delegates small app
builds to OpenAI Codex, keeping generated files and commands inside `sandbox/`.

## Before the timer

- Open `dist/Catbot-darwin-arm64/Catbot.app`. Keep this signed copy unchanged.
- Use Simple mode with Voice on, audible speakers and an internet connection.
- This timed script uses typed commands with spoken replies. Physical microphone
  input is optional and was not part of this rehearsal.
- Keep the existing Codex-built counter open in Safari:
  `sandbox/chai-probe-0e0b08bb/index.html`. Reset it to zero. It was built before
  the pitch; do not describe the counter as being generated during this minute.
- Stage `Billu, ek screenshot lena` in the command input, without sending it.

## Script and actions

| Time | Do | Say |
| --- | --- | --- |
| 0–10s | Show Billu in Simple mode. | “Meet Catbot. Billu is our grumpy Delhi desktop buddy. He understands Hinglish, talks back, and gets things done.” |
| 10–23s | Send `Billu, ek screenshot lena`. Let Billu finish. Click **View screenshot**, then close the preview using its red close button. | “Here’s a real desktop screenshot, saved inside his sandbox.” |
| 23–38s | Click **Full dashboard**. Send `Billu, saari files delete kar do`. Point to **BLOCKED** and let his refusal finish. | “Every action passes a policy gate. Dangerous requests stop before execution.” |
| 38–53s | Switch to the Safari counter. Click **+ 1 chai** twice, **− 1 chai** once, then **Reset tally**. Values: 0 → 1 → 2 → 1 → 0. | “Before this pitch, I asked Billu to build a chai counter. He delegated it to OpenAI Codex. This is the working result.” |
| 53–60s | Return to Catbot and select **Simple mode**. | “Sarvam gives him a voice, Laya checks proposed actions, and Codex builds. Useful work, visible guardrails, and a little Delhi attitude.” |

Leave space for Billu's replies; talk while opening the preview or switching apps.
The slots are presenter pacing targets, not a promise about network latency.
If the screenshot runs past 23 seconds, skip opening its preview and continue
once the request finishes. Do not queue another command while Billu is busy.

## Rehearsal evidence: 1 November 2026

All proposed interaction steps were exercised through the real native UI:

- Simple mode → Full dashboard → Simple mode worked.
- Exact screenshot command passed normal Sarvam/Laya/policy processing. One
  screenshot tool execution produced a real 3024×1964 PNG. Opened its preview
  and visually verified the desktop. Command to completed voice reply: **4.89s**.
- Exact destructive request received `tier_t3` immediately, with **zero tool
  executions**. Completed spoken refusal: **10.95s** from command submission.
- Both replies received completed audio-playback receipts from the app.
- Safari pointer clicks verified the existing counter's full sequence
  **0 → 1 → 2 → 1 → 0**. Counter left at zero.
- The counter is real output from an earlier Codex build, which took about 60s.
  A new build was not launched during this rehearsal.
- Python checks: **96 passed**; Electron checks: **19 passed**; Ruff clean.
  Fake full-demo rehearsal also passed three consecutive runs.

Private event evidence and captured images remain under ignored `sandbox/`.
The native app was restarted to load the shorter screenshot reply; its binary
was neither rebuilt nor re-signed. This tests the individual steps and measured
responses, not a recorded 60-second spoken presentation.
