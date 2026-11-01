# Final UI audit

2026-11-01. This audit walks the design law supplied with the task, alongside
`DESIGN.md` and the product requirements. It distinguishes source checks from
visual checks. **No browser screenshot, real pointer, physical microphone or
loudspeaker verification was possible:** the browser access host was unavailable
and native Safari access was not approved. Those checks remain open. This file
must not be read as a claim that pixel-level inspection passed.

The product-specific `DESIGN.md` explicitly specifies the supplied Gloock/Urbanist/
Inter fonts, exact dark palette, bento layout, stage colors, functional line icons,
rounded pipeline stages and rotated verdict sticker. Those deliberate brief
choices take precedence over the law's defaults. No marketing template was added.

## Identity, composition and typography

| Law point | Result and evidence |
| --- | --- |
| Avoiding the list is not design; recycling a house style; same skeleton recolored | The page is a working desktop-agent console. Billu's authored SVG and actual gate events are its signature. No landing-page section stack. |
| One signature artifact | Billu has a torn ear, backwards cap, glasses, whiskers, scar, neck headphones, expressive eyes, paw and mime tape. `ui/cat.svg`. |
| Atmosphere rather than a flat fill; flat fill after hero | Fine grain is on panel backgrounds, behind content. A restrained, stage-responsive cat aura is the specific design-brief exception. This is an operational dashboard, not a photo landing page. |
| Layered depth; product as real populated artifact; fake app window | The interface is the actual product. It displays real event, policy, tool and coding state, without traffic-light chrome or pretend screenshots. |
| Bespoke silhouette and geometry | The cat silhouette and cap are authored; the verdict is a rotated label. No gratuitous notch cuts near live text. |
| Treated navigation | Compact brand/connection/runtime/action header. Every action has a real purpose; no filler links. |
| Specifics and honest social proof | Actual Sarvam, Laya, Codex and Exa names; real measured timings and honest keyword fallback. No invented customers, avatars, testimonials or performance claims. |
| Lucide package; redrawn stock icons; no icons at all; custom iconography | Local functional SVG marks follow the explicit icon brief. No package/CDN or icon tiles. Billu himself is custom artwork; functional marks are not falsely presented as bespoke. |
| Fraunces/Work Sans; Space Grotesk; Cormorant; Sora/JetBrains; Syne; Archivo/Inter everywhere; Didones; Google font rotation; tasteful font swap | None added. Gloock and Urbanist are the supplied, explicitly required identity; Inter is limited to data. Only regular 400 is used for Gloock. |
| Monospace as house voice; one label treatment everywhere | Mono is restricted to arguments and actual process data. Other metadata uses the UI family with role-based weight and size. |
| Letterspaced serif wordmark; oversized footer wordmark, good and bad | The small product wordmark follows the brief. No oversized footer wordmark or cropped display signature. |
| Cramped display type; multiline/dangling accent headline | State headlines are short, fluid and at most a controlled two lines at phone width. No colored dangling word or extreme negative tracking. |
| Split hero; default hero stack; hero with right panel | No marketing hero. The dashboard composition follows the product-specific bento brief, with live decision panels rather than decorative props. |
| Hero owning first screen | The first frame is deliberately an application dashboard. Content below remains scrollable; no marketing half-section is used as accidental decoration. Pixel composition at actual viewport sizes remains unverified. |
| Kicker plus H2; label over heading; big serif statement | Section names label actual process areas. No repeated eyebrow/headline stack, decorative kicker or serif philosophy block. |
| Standard footer; content flung to edges | Three modest provenance/territory strings share the page grid. No wordmark-and-link-column template. |
| Whole SaaS skeleton; stacking slop layouts | No feature trio, pricing tiers, FAQ, testimonial row or CTA slab. |
| Image caption cards; inset enquiry island; email-pill form | Not applicable. The sole input is the real command control. |
| Numbered steps on a vertical rail | No such rail. Section numerals are required by the design brief and identify actual pipeline areas. |
| Unrounded ornamental rules; eyebrow tick; accent-bar cards | No ornamental label lines, card accent bars or vertical process rules. Bars represent actual classifier confidence. |
| Em dashes and ornamental quotation marks | Interface copy uses short direct sentences. No ornamental quote glyphs or AI-style prose framing. |

## Color, material and imagery

| Law point | Result and evidence |
| --- | --- |
| Purple/blue gradients; cool blue-charcoal; saturated accent sprayed everywhere | Exact supplied tokens are retained as an explicit brief choice. Stage colors have distinct semantic roles. No purple background gradient or gradient headline. |
| Cream/beige; UI-kit gray; pastel candy background; drifting candy blobs | None used in the dashboard. Fake app uses a separate, coherent muted green tapri palette. |
| Colliding colors and hard seams | One token system across the page. Stage colors encode separate events, not competing decorative accents. |
| Gradient icon lockup; gradient pill/icon label; gradient initials | None. Bare wordmark, bare functional marks, no fake avatar. |
| Gradient-filled headline | Absent. |
| Background glow; clipped glow; centered radial halo | One conic stage aura is specifically requested by `DESIGN.md`; it is low opacity, behind Billu, inside generous spacing. No CTA/card glow system or concentric hero halo. Pixel falloff remains unverified. |
| Glass, botched blur and resting halos | No glass or backdrop blur. Only the requested cat atmosphere is blurred. |
| Default all-around shadow; shadow as duplicated box; hard-edged shadow; blurred shape bloom | No duplicate shadow elements. Panels use only the provided shadow token. No hover shadow bloom. |
| Hairline border on every box | Panels retain the explicitly specified quiet surface border. No additional border-wrapped stat/tag kit. |
| Grid/graph-paper background; faint grid restatement; fixed following background | No grid, fixed ASCII sheet, blueprint wallpaper or drifting blob field. |
| Crude CSS/SVG illustration; crafted SVG | The SVG is a detailed character serving real state, rather than a placeholder chart or orbit illustration. Small orbit dots indicate actual thinking only. |
| Grain over content; premium noise; grainy gradients | Grain is a low-opacity background-image on the substrate. Text and controls remain above it. No page gradient requiring dither. |
| Hard photographic seams | No full-bleed photography, so not applicable. |
| Real logos and social icons; missing/faked marks | No customer/social claim requires a logo wall. Integrations are named honestly. No invented logo or mark-in-tile. |
| Icon or logo in a box | Functional SVG icons sit bare beside text. No colored icon containers. |
| Accent-border glow and inner-glow badges | No glowing badges, pulsing live-dot ring or fake elevation strips. The connection dot is solid and semantically labeled. |
| Legibility and contrast | Primary/muted/on-accent colors use the supplied high-contrast tokens. Faint color is decorative only. Removed reduced opacity on skipped pipeline labels. Browser contrast sampling remains open. |

## Interaction, motion and layout correctness

| Law point | Result and evidence |
| --- | --- |
| Hidden entrance-animation trap | All text and controls are visible by default. No opacity-zero entrance, observer gate, view timeline or hydration reveal. |
| Floating cards and meaningless motion | No floating cards. Cat breathing/aura and live microphone response are the only ambient motion; task states drive expression changes. |
| Hover boop; card hover lift | No button lift/scale, card translate or shadow bloom. Hover changes tone only. |
| Underline fill and botched fill animations | No animated underlines. Confidence uses measured data and scaleX on a full-width stable track as the explicit design brief requires. |
| Dot under active navigation | No decorative active-nav dot. Log filter uses a real pressed state. |
| Sun/moon toggle | No theme toggle. Voice control states exactly whether audio playback is enabled. |
| Dead controls/fake interactivity | Every rendered control is wired: text, PTT, voice, pet, chai, help/examples, confirmation, correction, filters, result/process details and app link. API/WebSocket paths have executable checks. **Actual pointer verification remains blocked.** |
| Content cut by edges; clear the cut; overlap clipping | No clip-path, notched content container or overflow-hidden text region. Scrollable code/log areas preserve their content. SVG bounds and rotated sticker have padding. Pixel-edge checks remain open. |
| Misaligned comparison columns | No comparison/pricing columns. Classifier rows use the same two-column structure and threshold tracks. |
| Text jammed at edge; far-edge imbalance | Desktop/tablet/phone gutters are explicit; panels have padding and min-width:0; preformatted data wraps or scrolls internally. |
| Centering | Cat viewport, SVG group axes, button icons and verdict contents have explicit geometric/flex centering. Optical centering still needs a screenshot check. |
| Off-center strike | No strike-through or redaction bar in the UI. Secrets are replaced with literal redacted text in logs. |
| Labels as tinted pills everywhere; kitchen-sink card | Status/source are mainly plain type. Rounded pipeline items are explicitly required and encode real state. No tag-filled price/feature card. |
| Default button pair; filled-plus-outlined pair; glowy pill buttons | No generic marketing CTA pair. Confirmation offers yes/cancel as solid surfaces, with meaningful labels. PTT's pill shape is specifically required. |
| Pricing, testimonial and pre-footer CTA presets | Absent. |
| Countdown urgency | Only a real confirmation expiry is counted, matching the backend deadline. No sale/drop urgency timer. |
| Reduced motion | Global reduced-motion tokens disable animations and transitions; pupil follow is explicitly disabled. No content depends on animation. |
| Authored motion, not lifeless | Billu changes eyes, ears, head, tail, raised paw and tape with actual stage/mood/mime events; microphone rings respond to RMS level. |
| Accessible feedback and errors | Visible text accompanies stage color. Denial uses alert semantics, final transcript is polite live content, dialogs are named, input has a label, focus is visible, and error/result states remain truthful. |
| Keyboard/touch | Space is excluded in text fields; Cmd/Ctrl K focuses input. Petting supports held Enter or Space. Primary controls meet 44px targets. PTT releases tracks and stops on blur/timeout/disconnection. |
| Responsive layout | Source reviewed for 375px, tablet and desktop breakpoints. Pipeline overflow is internal; code wraps. Actual 375px overflow and tap-target measurement remain open. |
| Indic fallback | Local Latin fonts retain Nirmala UI/Kohinoor Devanagari fallbacks. The Hindi command is covered by text/voice routing tests; actual glyph rasterization remains open. |

## Premium techniques considered, with restraint

Real translucency, self-colored elevation, invented geometry, signature type,
full-page scale, bespoke SVG, truthful product data, bare marks and authored
interaction were considered against this brief. The chosen subset is the custom
character, supplied type/palette, textured surfaces, semantic stage light and
live pipeline. No glass, paid type substitution, logo wall, inset signup island,
ASCII field, gradient-icon jewel or decorative scroll reveal was added merely to
satisfy a technique checklist. The page stays a coherent local agent application.

## Verification evidence

- Policy, executor, concurrency, server, voice and persona tests pass.
- Three fake rehearsals passed all five beats and unmute.
- Real Codex build completed in 65.96 seconds; generated counter handlers passed
  logic checks. Real STT/chat/Laya/TTS pipeline passed with fake desktop actions.
- PCM resampling passed at 44.1 and 48 kHz. JS modules parse successfully.
- HTML has no duplicate IDs, missing JS control targets or external asset URLs.
- `.env`, sandbox files and model weights remain untracked/ignored.
- Browser/pointer/pixel and physical audio verification: **open, not claimed**.
