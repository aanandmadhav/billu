# Catbot Design System — "Neon Noir Bazaar"

Source of truth for the look of everything in `catbot/ui/`. Where this file and `docs/SPEC.md` differ on which cards exist, the spec wins.

Generated with the ui-ux-pro-max skill (base: Dark Mode OLED + real-time ops dashboard pattern), then pushed to a custom direction built on the team's own fonts.

---

## 1. Direction (read this first)

**One line:** a late-night Delhi street-market sign meets a Bloomberg terminal, hosted by a cat.

- **Sleek:** near-black ink canvas, hairline borders, generous negative space, one bento grid, tabular numbers.
- **Premium:** an editorial serif (Gloock) at huge sizes against a precise sans (Urbanist). Warm paper-white text, not pure #FFF. Film grain.
- **Funky:** acid "catnip" lime as the hero accent, rotated sticker badges for verdicts, Hinglish micro-copy, a cat whose eyes and aura change color with every pipeline stage, a marquee transcript ticker.

**Product job of the UI:** the judges must *see* Laya decide. The Decision Panel and Pipeline Rail are the heroes. The cat is the personality. Everything else supports.

**Do not:** light mode, purple-gradient-on-white "AI" look, emoji as icons, glassmorphism on everything, more than 2 continuously animated elements in view, glitch effects on text people need to read.

---

## 2. Fonts

The font files are in `assets/fonts/`. Copy them to `catbot/ui/fonts/`:

| Source | Copy to | Notes (verified with fontTools) |
| --- | --- | --- |
| `assets/fonts/gloock.woff2` | `ui/fonts/gloock.woff2` | Gloock Regular, **static, one weight only (400)**. Never set `font-weight: 700` on it (faux bold looks cheap). |
| `assets/fonts/urbanist.woff2` | `ui/fonts/urbanist.woff2` | Urbanist, **variable `wght` 400–800**. Latin only. |
| `assets/fonts/urbanist-italic.woff2` | `ui/fonts/urbanist-italic.woff2` | Urbanist Italic, variable 400–800. |
| `assets/fonts/inter-var.ttf` | `ui/fonts/inter-var.ttf` | Inter variable (`opsz`, `wght`). Used only for numbers and data (tabular figures). |

**None of these fonts contain Devanagari or Tamil glyphs** (checked: U+0915 missing). Every stack must end in an Indic fallback. Windows 11 ships `Nirmala UI` (covers Devanagari + Tamil). macOS ships `Kohinoor Devanagari` and `Tamil Sangam MN`.

```css
@font-face { font-family: "Gloock"; src: url("fonts/gloock.woff2") format("woff2");
  font-weight: 400; font-style: normal; font-display: swap; }
@font-face { font-family: "Urbanist"; src: url("fonts/urbanist.woff2") format("woff2");
  font-weight: 400 800; font-style: normal; font-display: swap; }
@font-face { font-family: "Urbanist"; src: url("fonts/urbanist-italic.woff2") format("woff2");
  font-weight: 400 800; font-style: italic; font-display: swap; }
@font-face { font-family: "Inter"; src: url("fonts/inter-var.ttf") format("truetype");
  font-weight: 100 900; font-style: normal; font-display: swap; }

:root {
  --font-display: "Gloock", "Nirmala UI", "Kohinoor Devanagari", Georgia, serif;
  --font-ui:      "Urbanist", "Nirmala UI", "Kohinoor Devanagari", system-ui, sans-serif;
  --font-data:    "Inter", "Nirmala UI", system-ui, sans-serif;
  --font-code:    "Cascadia Code", Consolas, ui-monospace, monospace;
}
```

Preload only `gloock.woff2` and `urbanist.woff2` (`<link rel="preload" as="font" type="font/woff2" crossorigin>`).

### Roles

| Role | Font | Use |
| --- | --- | --- |
| Display | Gloock 400 | Wordmark, cat state headline ("Ho gaya."), section numerals, big confidence % |
| UI | Urbanist 500–700 | Everything else: labels, body, buttons, transcript |
| Accent | Urbanist Italic 600 | Hinglish asides, sticker text, the "funky" voice |
| Data | Inter 500, `font-variant-numeric: tabular-nums` | Confidences, latencies (ms), timestamps, counters |
| Code | Cascadia/Consolas | Tool args JSON, Task Brief JSON |

### Type scale (fluid, px at 1440 → 375)

| Token | Size | Line height | Tracking | Font |
| --- | --- | --- | --- | --- |
| `--t-mega` | `clamp(56px, 9vw, 132px)` | 0.92 | -0.03em | Display |
| `--t-h1` | `clamp(36px, 4.5vw, 64px)` | 1.0 | -0.02em | Display |
| `--t-h2` | `clamp(24px, 2.4vw, 32px)` | 1.1 | -0.01em | Display |
| `--t-h3` | 18px | 1.3 | 0 | UI 700 |
| `--t-body` | 16px | 1.55 | 0 | UI 500 |
| `--t-small` | 14px | 1.45 | 0.01em | UI 500 |
| `--t-label` | 12px | 1.2 | 0.14em, uppercase | UI 700 |
| `--t-data-xl` | `clamp(40px, 5vw, 72px)` | 1 | -0.02em | Data 600 |
| `--t-data` | 14px | 1.3 | 0 | Data 500 |

Body text never below 14px. Labels at 12px only in uppercase with tracking and `--c-muted` or brighter.

---

## 3. Color tokens

Contrast numbers are WCAG ratios, computed against the three surfaces (bg / surface-1 / surface-2).

```css
:root {
  color-scheme: dark;

  /* canvas */
  --c-bg:        #0B0A10;   /* ink */
  --c-surface-1: #14121C;   /* cards */
  --c-surface-2: #1C1A27;   /* raised, inputs, hover */
  --c-line:      rgba(244, 239, 230, 0.08);
  --c-line-strong: rgba(244, 239, 230, 0.16);

  /* text */
  --c-paper:  #F4EFE6;   /* primary text      17.2 / 16.2 / 15.0 */
  --c-muted:  #A9A4B8;   /* secondary text     8.2 /  7.7 /  7.1 */
  --c-faint:  #7C778C;   /* decorative / >=18px only: 4.6 / 4.3 / 4.0 */

  /* brand + stage accents (all >= 5.4:1 on every surface) */
  --c-catnip:  #C6FF3D;  /* hero accent, allow, act, done        16.7 */
  --c-saffron: #FFA62B;  /* confirm, asking, ask_followup        10.1 */
  --c-chili:   #FF5468;  /* deny, blocked, destructive            6.3 */
  --c-magenta: #FF5BD8;  /* listening, voice, transcript          7.3 */
  --c-violet:  #9C8CFF;  /* Laya, routing, thinking               7.1 */
  --c-cyan:    #5EE6EB;  /* tools, args, results, data            13.1 */

  --c-on-accent: #0B0A10; /* text on any filled accent: >= 6.3:1 */

  /* glows (use sparingly: active element only) */
  --glow-catnip:  0 0 0 1px rgba(198,255,61,.35), 0 0 32px rgba(198,255,61,.18);
  --glow-violet:  0 0 0 1px rgba(156,140,255,.35), 0 0 32px rgba(156,140,255,.18);
  --glow-saffron: 0 0 0 1px rgba(255,166,43,.40), 0 0 32px rgba(255,166,43,.20);
  --glow-chili:   0 0 0 1px rgba(255,84,104,.45), 0 0 32px rgba(255,84,104,.22);
  --glow-magenta: 0 0 0 1px rgba(255,91,216,.40), 0 0 32px rgba(255,91,216,.20);
}
```

Never put raw hex in component CSS. Use the tokens.

### Stage → color map (single source, used by rail, cat aura, log dots)

| Stage | Token | Cat state |
| --- | --- | --- |
| idle (no task for 20 s) | `--c-faint` | sleeping |
| listen | `--c-magenta` | listening |
| think | `--c-violet` | thinking |
| risk, gate (pending) | `--c-saffron` | thinking |
| gate → allow | `--c-catnip` | thinking |
| gate → confirm, confirm | `--c-saffron` | asking |
| gate → deny, any error | `--c-chili` | blocked |
| execute, result | `--c-cyan` | thinking |
| speak, done ok | `--c-catnip` | done |

Color is never the only signal: every stage also has a label and an icon.

---

## 4. Space, radius, elevation, z-index

```css
:root {
  --s-1: 4px; --s-2: 8px; --s-3: 12px; --s-4: 16px; --s-5: 24px;
  --s-6: 32px; --s-7: 48px; --s-8: 64px; --s-9: 96px;

  --r-sm: 8px; --r-md: 14px; --r-lg: 22px; --r-xl: 32px; --r-pill: 999px;

  --shadow-card: 0 1px 0 rgba(244,239,230,.04) inset, 0 24px 48px -24px rgba(0,0,0,.6);

  --z-base: 0; --z-card: 10; --z-sticky: 20; --z-overlay: 40; --z-sheet: 100; --z-toast: 1000;
}
```

Cards: `background: var(--c-surface-1); border: 1px solid var(--c-line); border-radius: var(--r-lg); box-shadow: var(--shadow-card); padding: var(--s-5);`. Active card adds the stage glow. No other shadow values.

---

## 5. Motion

```css
:root {
  --ease-out: cubic-bezier(.16, 1, .3, 1);     /* enter */
  --ease-in:  cubic-bezier(.7, 0, .84, 0);     /* exit */
  --ease-spring: cubic-bezier(.34, 1.56, .64, 1); /* stickers, cat pop */
  --d-fast: 140ms; --d-base: 220ms; --d-slow: 380ms;
}
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after { animation-duration: .001ms !important; animation-iteration-count: 1 !important;
    transition-duration: .001ms !important; scroll-behavior: auto !important; }
}
```

Rules:

- Animate only `transform` and `opacity` (and `filter` for the aura).
- Continuous animations allowed: cat breathing/aura, and the listening waveform. Nothing else loops.
- Laya bars fill with `transform: scaleX()` over `--d-slow`, staggered 40 ms per bar.
- Rail stages light up in sequence as events arrive; never fake progress.
- Sticker badges enter with `--ease-spring` scale 0.6 → 1 and rotate to their resting angle.
- Exit = ~65% of enter duration.
- Reduced motion: cat shows state by pose and color only; bars appear filled; ticker stops.

---

## 6. Layout

**Simple mode (user direction):** The button beside Billu's name switches to a centered companion area with Billu, his reply/transcript and the text/voice composer. Hide the top bar and activity panels. The same button becomes Full dashboard. Preserve active confirmations, coding feedback and generated-app links in the companion area; give-chai controls appear when Billu requests them. The desktop preference lives in Electron user data rather than the changing local server origin. Settings remain accessible by returning to the dashboard.

**Current desktop layout (user direction):** At 850px and wider, keep Billu's chat and command area in a stationary left pane. The right activity pane contains the permission setup and all decision panels, including 04 (Billu's plan) and 07 (What just happened), and scrolls independently. The footer belongs to that right pane. On short windows or enlarged text, the left pane may scroll internally so controls remain reachable. Smaller screens retain the flowing responsive layout. This supersedes the desktop grid placement below.

Single page, `min-height: 100dvh`, max content width 1440px, side gutter `--s-5` (16px under 640px).

### Desktop ≥ 1200px (12-column bento, gap `--s-4`)

```text
┌──────────────────────────────────────────────────────────────────────────────┐
│ catbot.  ● live   gate: KEYWORD · shadow · ckpt: english · os: macos  [?]   │  top bar (sticky)
├───────────────────────────────┬──────────────────────────────────────────────┤
│                               │  01 PIPELINE                                 │
│        (  CAT STAGE  )        │  listen › think › risk › gate › confirm ›    │
│     big SVG cat + aura        │  execute › result › speak   (pill + ms)      │
│                               │                                   412 ms     │
│   "Ek second…" (Gloock)       ├──────────────────────────┬───────────────────┤
│                               │  02 LAYA DECIDES         │  03 VERDICT       │
│  ~~~ transcript ticker ~~~    │  tier       T1  ▇▇▇▇ 100 │  ┌─────────────┐  │
│                               │  verify execute ▇▇▇▇  90 │  │  ALLOWED ✓  │  │  sticker
│ [ hold SPACE to talk ]        │  reply       A  ▇▇▇▇  92 │  └─────────────┘  │
│ [ or type… ⏎ ]                │  chip: keyword · 3 ms    │  policy: allow    │
│  cols 1–5, rows 1–3           │  floor: T2               │  reason: …        │
├───────────────────────────────┼──────────────────────────┴───────────────────┤
│ 04 PLAN (think text per step) │ 05 TOOL CALL  run_command  argv [...]        │
│ 1 Creating the folder.        │ 06 RESULT  ✓ "exit 0"  origin: command_output│
├───────────────────────────────┴──────────────────────────────────────────────┤
│ 07 LOG  (virtualised list, newest first)          │ TRAINING  12 corrections │
└──────────────────────────────────────────────────────────────────────────────┘
```

- Cat Stage: columns 1–5, spans the first three rows, `position: sticky; top: 72px`.
- Right side: columns 6–12.
- Section numerals `01 … 07` set in Gloock, `--c-faint`, `--t-h2`. This is the editorial signature.

### Tablet 768–1199px

Cat Stage on top (full width, 320px tall, cat left / transcript right). Then Pipeline full width, then Laya + Verdict side by side, then Brief, Call, Result stacked, then Log.

### Phone 375–767px

Single column in priority order: Cat Stage (240px) → Command bar (sticky bottom, safe-area padded) → Verdict → Laya → Pipeline (horizontal scroll *inside* the card only, with fade masks) → Result → Call → Brief → Log. No page-level horizontal scroll.

---

## 7. Components

### 7.1 Top bar

`catbot.` wordmark in Gloock 28px, period in `--c-catnip`. Live dot: catnip when WebSocket open, chili + "offline, reconnecting…" when closed (auto-reconnect with backoff 1s→8s). Chips (Inter 12px, pill, `--c-surface-2`): router (`LAYA`/`KEYWORD`), last checkpoint, `TARGET_OS`. Buttons: command palette (focus text input), help (keyboard shortcuts sheet).

### 7.2 Cat Stage (hero)

- The SVG cat (section 8), 280–360px, centred, inside an **aura**: a blurred `conic-gradient` disc behind the cat using the current stage color, `filter: blur(48px); opacity: .55`, slowly rotating (20 s per turn; stops under reduced motion).
- Film grain over the whole page: one inline SVG `feTurbulence` noise as a fixed `::after` on `body`, `opacity: .05`, `pointer-events: none`, `mix-blend-mode: overlay`.
- **State headline** under the cat, Gloock `--t-h1`, in the user's language when known:

| State | Headline (hi / hinglish) | Headline (en) | Sub-line (Urbanist italic, muted) |
| --- | --- | --- | --- |
| sleeping | `Zzz…` | `Zzz…` | hold Space to wake me |
| listening | `Bolo, sun rahe hain.` | `Listening.` | live transcript |
| thinking | `Ek second…` | `On it…` | current stage name + ms |
| asking | `Pakka?` | `Sure?` | the confirmation question |
| blocked | `Nahi hoga.` | `Not doing that.` | policy reason |
| done | `Ho gaya.` | `Done.` | result summary |

  (Hindi copy avoids gendered verb endings for the cat on purpose.)
- **Transcript ticker:** partial text in `--c-magenta` Urbanist 600 22px, final text in `--c-paper`. If longer than the box, it scrolls as a marquee (pauses on hover/focus, static under reduced motion). `aria-live="polite"` on final text only.
- **Push-to-talk button (user layout override):** a compact 48px microphone button to the right of the chat input and send action, with the full hold/release instructions in its accessible label and tooltip. It matches the input radius and stays on the same row on small screens. Former full-width placement is superseded. Uses `--c-surface-2`, label "Hold Space to talk" + mic icon. While held: fill `--c-magenta`, text `--c-on-accent`, waveform bars animate from mic RMS level sent in `listen` events (`payload.level`, 0–1). Keyboard: Space held when focus is not in a text field. Mouse/touch: pointerdown/pointerup.
- **Text input** alongside it: "or type… volume kam karo" placeholder plus a visible label "Type a command" (visually small, not placeholder-only). Enter submits to `POST /api/text`.

### 7.3 Pipeline Rail (01)

8 pills in a wrapping row: `listen think risk gate confirm execute result speak`, connected by a 1px `--c-line` track. Each pill: icon + stage name (Urbanist 600 14px) + latency (Inter tabular 12px, muted). A ReAct task may pass `think → … → result` several times; the pills show the latest pass and a small step counter (`step 2`).

- States: `pending` (faint outline), `active` (filled with stage color at 14% alpha, border in stage color, glow, icon pulses once), `done` (border in stage color, check mark), `skipped` (dashed outline, e.g. `confirm` when the gate allowed), `failed` (chili, e.g. `gate` on deny).
- Total task latency at the end in `--t-data-xl` Inter, catnip: e.g. `412 ms`.

### 7.4 Laya Decides (02) — the hero card

One row per decision: label (12px uppercase muted) · choice (Urbanist 700 18px, paper) · bar · confidence % (Inter tabular 600 18px) · source chip.

- **3 rows:** `tier` (T0–T3, from `risk.payload.tier`), `verify` (execute / wrong_tool / unclear), `reply` (A / B / C, only when a confirm happened).
- Bar: 8px tall, `--r-pill`, track `--c-surface-2`. Fill: ≥ threshold catnip, within 0.2 below it saffron, lower chili. Threshold tick at **0.80 on tier** and **0.70 on verify** (1px `--c-line-strong`).
- Source chip per row: `laya` (violet), `keyword` (saffron, so nobody mistakes it for Laya) or `shadow` (outline). When `payload.shadow` is present, a second thin bar under the tier row shows the shadow Laya tier and confidence.
- Footer: utterance floor chip (`floor: T2`), checkpoint chip, latency in ms.
- Correction affordance: each row has a small "wrong?" text button → a popover listing the valid choices → `POST /api/correction`. Counter in the Log card increments. This is the data flywheel shown live.

### 7.5 Verdict (03) — sticker

Big rotated sticker (`transform: rotate(-4deg)`), `--r-md`, filled with verdict color, text `--c-on-accent`, Urbanist Italic 800 28px uppercase with a 2px dashed inner border in `rgba(11,10,16,.35)`:

- allow → catnip, "ALLOWED" + check icon
- confirm → saffron, "PUCHHNA PADEGA" / "NEEDS A YES" + question icon; card shows **Confirm** (catnip filled) and **Cancel** (outline) buttons that `POST /api/confirm`; 8 s countdown ring around the sticker.
- deny → chili, "BLOCKED" + shield icon, slight 2-frame shake (disabled under reduced motion).

Below the sticker: `verdict.policy` (code font), `reason` (body), and `corrective_context` in a muted inset if present. Provenance chip when the last result origin ≠ user: e.g. "origin: screen — data only", cyan outline; chili "instruction-like text" chip when `provenance_flag` is true.

### 7.6 Plan (04)

Header row: lang chip (from `listen`/`speak` payloads), step count. Body: numbered list, one line per `think` event, showing the assistant's English sentence (`payload.text`) and the tool it chose. The current step is highlighted in violet. The final reply (no tool call) is the last line in catnip.

### 7.7 Tool Call (05) and Result (06)

- Call: `tool` in Urbanist 700, risk tier chip (T0 cyan, T1 cyan, T2 saffron, T3 chili), args as key/value rows (code font), and the exact `argv` from the `execute` payload as a code line.
- Result: ok icon (check/x), summary in `--t-h3`, origin chip, latency, collapsible `data`.

### 7.8 Log (07) + Training counter

Newest first, one line per event: time (Inter tabular, muted) · colored stage dot · stage · agent/tool · verdict · ms. Keep only the latest 500 in the DOM. Filter chips: all / decisions / gate / errors. Training counter: Gloock numeral in catnip + "corrections logged for training".

### 7.9 Confirmation sheet (phone only)

On phones the confirm buttons move into a bottom sheet with a 50% black scrim, dismiss = Cancel.

### 7.10 Icons

Lucide (inline SVG, copy the paths you need into `ui/icons.js`; no CDN, no build step). Stroke 1.75, size tokens 16 / 20 / 24. Map: listen `mic`, think `brain`, risk `gauge`, gate `shield`, confirm `circle-help`, execute `zap`, result `list-checks`, speak `volume-2`, deny `shield-x`, allow `shield-check`.

---

## 8. The cat (SVG)

One inline SVG, `viewBox="0 0 320 320"`, root `<svg id="cat" data-state="sleeping" role="img" aria-label="Billu is sleeping">`. Flat geometric cat, front facing, sitting. Body `--c-surface-2` with a 2px `--c-line-strong` stroke, inner ears and nose in the stage color, eyes in the stage color. Drawn from simple primitives (circles, ellipses, paths) so a small model can write it.

Groups (each a `<g>` with a class), and the state rules:

| Group | sleeping | listening | thinking | asking | blocked | done |
| --- | --- | --- | --- | --- | --- | --- |
| `.ears` | relaxed, rotated out 8° | perked up (translateY -4) | normal | one ear tilted | flattened back (rotate 18°) | normal |
| `.eyes-open` | hidden | visible, magenta | visible, violet, pupils look up-right | visible, saffron, wide | hidden | hidden |
| `.eyes-closed` (two arcs ︶) | visible | hidden | hidden | hidden | hidden | hidden |
| `.eyes-narrow` (two flat lines) | hidden | hidden | hidden | hidden | visible, chili | hidden |
| `.eyes-happy` (two ^ arcs) | hidden | hidden | hidden | hidden | hidden | visible, catnip |
| `.head` | tilted down 6° | upright | upright | tilted 10° | upright | upright |
| `.tail` | curled, still | slow sway | fast flick | question-mark curve | puffed (scale 1.15) | big swish once |
| `.zzz` | visible, floating | — | — | — | — | — |
| `.orbit` (3 dots around head) | — | — | rotating | — | — | — |
| `.paw-stop` (raised paw) | — | — | — | — | visible | — |
| `.sparkle` | — | — | — | — | — | 4 sparkles pop once |
| `.wave-ring` (concentric rings) | — | pulse with mic level | — | — | — | — |

Implementation: CSS only, keyed on `#cat[data-state="…"]`. JS sets `data-state` and updates `aria-label`. Pupils follow the pointer within ±4px (disabled under reduced motion and on touch devices). Breathing: body `scale(1 → 1.015)` over 4 s, ease-in-out, sleeping and listening only.

Skeleton to start from:

```html
<svg id="cat" data-state="sleeping" viewBox="0 0 320 320" role="img" aria-label="Billu is sleeping">
  <g class="aura-anchor"></g>
  <g class="tail"><path d="M220 250 C 280 250, 290 180, 250 160" fill="none" stroke-width="14" stroke-linecap="round"/></g>
  <g class="body"><ellipse cx="160" cy="245" rx="78" ry="58"/></g>
  <g class="head">
    <g class="ears">
      <path class="ear ear-l" d="M100 120 L112 60 L148 100 Z"/>
      <path class="ear ear-r" d="M220 120 L208 60 L172 100 Z"/>
    </g>
    <circle class="face" cx="160" cy="140" r="64"/>
    <g class="eyes-open"><ellipse cx="136" cy="138" rx="9" ry="12"/><ellipse cx="184" cy="138" rx="9" ry="12"/>
      <circle class="pupil" cx="136" cy="140" r="4"/><circle class="pupil" cx="184" cy="140" r="4"/></g>
    <g class="eyes-closed"><path d="M126 140 q10 8 20 0"/><path d="M174 140 q10 8 20 0"/></g>
    <g class="eyes-narrow"><path d="M126 138 h20"/><path d="M174 138 h20"/></g>
    <g class="eyes-happy"><path d="M126 142 q10 -10 20 0"/><path d="M174 142 q10 -10 20 0"/></g>
    <path class="nose" d="M154 160 h12 l-6 7 z"/>
    <g class="whiskers"><path d="M110 165 h-34"/><path d="M110 172 l-32 6"/><path d="M210 165 h34"/><path d="M210 172 l32 6"/></g>
  </g>
  <g class="orbit"><circle cx="160" cy="62" r="5"/><circle cx="232" cy="140" r="5"/><circle cx="88" cy="140" r="5"/></g>
  <g class="zzz"><text x="222" y="78">z</text><text x="240" y="56">z</text><text x="262" y="34">Z</text></g>
  <g class="paw-stop"><ellipse cx="240" cy="200" rx="22" ry="26"/></g>
  <g class="sparkle"><path d="M70 90 l4 10 10 4 -10 4 -4 10 -4 -10 -10 -4 10 -4z"/></g>
  <g class="wave-ring"><circle cx="160" cy="160" r="120" fill="none"/><circle cx="160" cy="160" r="145" fill="none"/></g>
</svg>
```

The cat colors come from one CSS custom property set on the stage container: `--stage-color`. JS sets it from the stage map in section 3.

---

## 9. Micro-copy (Hinglish first, English when the `lang` from `listen`/`speak` starts with `en`)

| Moment | Hinglish | English |
| --- | --- | --- |
| Empty log | "Abhi tak kuch nahi hua. Space dabao aur bolo." | "Nothing yet. Hold Space and speak." |
| WebSocket down | "Connection gaya. Dobara jod rahe hain…" | "Connection lost. Reconnecting…" |
| Low confidence | "Pakka nahi pata. Matlab {A} ya {B}?" | "Not sure. Did you mean {A} or {B}?" |
| Keyword fallback chip | "keyword fallback" | "keyword fallback" |
| Correction thanks | "Shukriya, yaad rakhenge." | "Thanks, logged for training." |

---

## 10. Accessibility checklist (the UI must pass all)

- [ ] All text pairs ≥ 4.5:1 (tokens above already pass; `--c-faint` only for decorative or ≥ 18px text).
- [ ] Visible focus ring everywhere: `outline: 2px solid var(--c-catnip); outline-offset: 3px;`.
- [ ] Skip link "Skip to decisions" as the first focusable element.
- [ ] Every icon-only button has `aria-label`.
- [ ] One `<h1>` (visually the wordmark), section titles are `<h2>`.
- [ ] Final transcript and verdict use `aria-live="polite"`; deny uses `role="alert"`.
- [ ] Space-to-talk does not fire while focus is inside an input; there is also a clickable PTT button.
- [ ] Touch targets ≥ 44×44px, ≥ 8px apart.
- [ ] `prefers-reduced-motion` honoured (section 5).
- [ ] Works at 375px with no page-level horizontal scroll.
- [ ] Devanagari text renders through the Nirmala UI fallback (test with "आवाज़ कम करो").

---

## 11. File layout for `catbot/ui/`

```text
ui/
  index.html      markup, inline cat SVG, no framework
  tokens.css      sections 2–5 of this file verbatim
  app.css         layout + components
  app.js          WebSocket client, state store, renderers (ES modules, no build)
  audio.js        mic capture (16 kHz int16 frames), TTS playback, barge-in
  icons.js        Lucide paths used (exported as strings)
  cat.svg         the cat (section 8), also inlined in index.html
  fonts/          copied font files
```

Plain ES modules (`<script type="module">`). No npm, no bundler, no CDN at runtime (the demo may be offline).
