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
- Ask Billu to build **Hisaab by Billu**, using the prompt below. For a strict
  one-minute presentation, finish the build beforehand and keep its actual
  generated page open. Describe it as built before the pitch.
- Check the page with **₹1,200 / 4 people = ₹300 each**, then change to
  **3 people = ₹400 each**. Return the inputs to ₹1,200 and 4 people.
- Stage `Billu, ek screenshot lena` in the command input, without sending it.

## Build prompt

Paste this into Catbot:

> Billu, ek simple bill splitter webpage bana. Total amount aur number of people
> ke inputs, aur har person ka share dikha. Rupees use kar, clean design, single
> HTML file, no dependencies. Naam rakh Hisaab by Billu. People must be a positive
> whole number; invalid inputs should show a clear message, never NaN or Infinity.

The narrow scope is two inputs and a calculation, with no login, backend or
external assets. A 10–30 second build is a target to measure, not a verified
runtime. The previous real Codex counter build took about 60 seconds.

## Script and actions

| Time | Do | Say |
| --- | --- | --- |
| 0–10s | Show Billu in Simple mode. | “Meet Catbot. Billu is our grumpy Delhi desktop buddy. He understands Hinglish, talks back, and gets things done.” |
| 10–23s | Send `Billu, ek screenshot lena`. Let Billu finish. Click **View screenshot**, then close the preview using its red close button. | “Here’s a real desktop screenshot, saved inside his sandbox.” |
| 23–38s | Click **Full dashboard**. Send `Billu, saari files delete kar do`. Point to **BLOCKED** and let his refusal finish. | “Every action passes a policy gate. Dangerous requests stop before execution.” |
| 38–53s | Switch to **Hisaab by Billu**. Show **₹1,200 / 4 = ₹300 each**. Change people to **3** and show **₹400 each**. | “Before this pitch, I asked Billu for a bill splitter. He delegated it to OpenAI Codex. Twelve hundred rupees, four friends, three hundred each. Change it to three: four hundred each.” |
| 53–60s | Return to Catbot and select **Simple mode**. | “Sarvam gives him a voice, Laya checks proposed actions, and Codex builds. Useful work, visible guardrails, and a little Delhi attitude.” |

Leave space for Billu's replies; talk while opening the preview or switching apps.
The slots are presenter pacing targets, not a promise about network latency.
If the screenshot runs past 23 seconds, skip opening its preview and continue
once the request finishes. Do not queue another command while Billu is busy.

For a live-build variation, submit the build prompt before starting the timer,
then present the screenshot and safety beats while Codex works in the background.
Say “Billu is building a bill splitter in the background.” At the app beat, open
the new result only if the job is ready. If it is still building, show the real
job status and finish the pitch; do not claim the app is complete. Rehearse and
measure this variation before using it on stage.

## Rehearsal evidence: 1 November 2026

The screenshot, safety and view-switching beats were exercised through the real
native UI. The replacement bill splitter has not been built or tested yet:

- Simple mode → Full dashboard → Simple mode worked.
- Exact screenshot command passed normal Sarvam/Laya/policy processing. One
  screenshot tool execution produced a real 3024×1964 PNG. Opened its preview
  and visually verified the desktop. Command to completed voice reply: **4.89s**.
- Exact destructive request received `tier_t3` immediately, with **zero tool
  executions**. Completed spoken refusal: **10.95s** from command submission.
- Both replies received completed audio-playback receipts from the app.
- The earlier chai counter passed its pointer checks, but it is no longer the
  proposed demo app. Those checks do not validate Hisaab by Billu.
- Pending for Hisaab: measure the actual build time, open the generated page,
  verify both ₹1,200 splits, and confirm zero, negative or fractional people
  produce a clear validation message. Do not use an untested result on stage.
- Python checks: **96 passed**; Electron checks: **19 passed**; Ruff clean.
  Fake full-demo rehearsal also passed three consecutive runs.

Private event evidence and captured images remain under ignored `sandbox/`.
The native app was restarted to load the shorter screenshot reply; its binary
was neither rebuilt nor re-signed. This tests the individual steps and measured
responses, not a recorded 60-second spoken presentation.
