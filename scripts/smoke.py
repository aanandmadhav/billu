"""Live P0 probes. Never dump requests, environment or credentials."""

import argparse
import json
import os
import subprocess
import time

from catbot.config import Settings
from catbot.contracts import GateToken, ToolCall
from catbot.gate.keyword import decision
from catbot.gate.policy import policy_gate


def permit(tool, args):
    call = ToolCall(
        task_id="p0",
        step=1,
        call_id="smoke",
        tool=tool,
        args=args,
        request_en="Run the explicitly requested live P0 integration smoke test",
    )
    token = GateToken(call_id=call.call_id, verdict=policy_gate(call, decision(call)))
    if token.call_id != call.call_id or token.verdict.verdict != "allow":
        raise PermissionError(token.verdict.reason)
    return token


def main(kind):
    settings = Settings.load()
    if kind == "sarvam":
        permit("set_volume", {"action": "down"})
        from sarvamai import SarvamAI

        client = SarvamAI(api_subscription_key=settings.sarvam_key)
        response = client.chat.completions(
            model="sarvam-105b",
            messages=[{"role": "user", "content": "volume kam karo"}],
            tools=[
                {
                    "type": "function",
                    "function": {
                        "name": "set_volume",
                        "description": "Change volume",
                        "parameters": {
                            "type": "object",
                            "properties": {"action": {"type": "string"}},
                            "required": ["action"],
                        },
                    },
                }
            ],
            tool_choice="auto",
            reasoning_effort=None,
            max_tokens=400,
        )
        print(response.model_dump_json())
    elif kind == "laya":
        permit("set_volume", {"action": "down"})
        os.environ["USE_TF"] = "0"
        import laya

        start = time.monotonic()
        agent = laya.Agent(str(settings.model_dir))
        print("load_seconds", round(time.monotonic() - start, 3))
        questions = json.loads((settings.model_dir / "questions.json").read_text())
        for request, tool, args in [
            ("lower volume", "set_volume", {"action": "down"}),
            ("delete all files", "run_command", {"command": "rm -rf ."}),
        ]:
            state = (
                f"Request: {request}\nAction: {tool} {json.dumps(args, ensure_ascii=False)[:400]}"
            )
            start = time.monotonic()
            response = agent.predict(state, {k: questions[k] for k in ("risk_tier", "verify_call")})
            print(json.dumps(response, default=str), "ms", round((time.monotonic() - start) * 1000))
    elif kind == "exa":
        permit("web_search", {"query": "Delhi cutting chai"})
        from exa_py import Exa

        response = Exa(api_key=settings.exa_key).search("Delhi cutting chai", num_results=3)
        print(
            json.dumps(
                {
                    "results": [
                        {"title": r.title, "url": r.url, "text": (r.text or "")[:160]}
                        for r in response.results
                    ]
                }
            )
        )
    elif kind == "codex":
        permit("write_code", {"app_name": "p0-smoke", "spec": "Make a one-line HTML greeting"})
        target = settings.sandbox / "p0-smoke"
        target.mkdir(exist_ok=True)
        result = subprocess.run(
            [
                "codex",
                "exec",
                "-m",
                "gpt-5.6-terra",
                "-C",
                str(target),
                "-s",
                "workspace-write",
                "--skip-git-repo-check",
                "--ephemeral",
                "--json",
                "-o",
                str(target / ".codex-last.txt"),
                "Write index.html containing only <h1>Billu says hello</h1>. Work only in this directory. No network or dependencies. Finish now.",
            ],
            cwd=target,
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )
        # Codex JSONL can contain environment context; emit only event shapes and final artifact.
        for line in result.stdout.splitlines():
            try:
                data = json.loads(line)
                item = data.get("item", {})
                print(
                    json.dumps(
                        {
                            "type": data.get("type"),
                            "item_type": item.get("type"),
                            "message": data.get("message", item.get("message", "")),
                        }
                    )
                )
            except ValueError:
                pass
        print("exit", result.returncode)
        print(
            "artifact",
            (target / "index.html").read_text() if (target / "index.html").exists() else "missing",
        )
        if result.returncode:
            print("Codex could not complete. Check codex login status and local CLI configuration.")
    elif kind == "tts":
        permit("set_volume", {"action": "down"})
        from sarvamai import SarvamAI

        response = SarvamAI(api_subscription_key=settings.sarvam_key).text_to_speech.convert(
            text="Billu bol raha hoon. Ho gaya.",
            language_code="hi-IN",
            model="bulbul:v4-flash",
            speaker="ratan_hi_social",
            speech_sample_rate=24000,
            output_audio_codec="wav",
        )
        print({"audios": len(response.audios), "base64_length": len(response.audios[0])})
    elif kind == "stt-shape":
        permit("web_search", {"query": "Inspect installed Sarvam STT SDK"})
        import inspect

        from sarvamai import AsyncSarvamAI, RealtimeAudioInput, RealtimeEnd

        print(
            inspect.signature(
                AsyncSarvamAI(
                    api_subscription_key=settings.sarvam_key
                ).speech_to_text_realtime_streaming.connect
            )
        )
        print(RealtimeAudioInput.model_fields.keys(), RealtimeEnd.model_fields.keys())


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("kind", choices=["sarvam", "laya", "codex", "exa", "tts", "stt-shape"])
    try:
        main(parser.parse_args().kind)
    except Exception as exc:  # noqa: BLE001 - redact service errors at the CLI boundary
        print("PROBE FAILED:", type(exc).__name__)
        raise SystemExit(1) from None
