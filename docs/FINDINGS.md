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
