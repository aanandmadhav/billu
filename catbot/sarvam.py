import asyncio
import json
import re
from uuid import uuid4

from catbot.tools.registry import TOOLS


class Sarvam:
    def __init__(self, settings):
        from sarvamai import SarvamAI

        self.client = SarvamAI(api_subscription_key=settings.sarvam_key)

    async def chat(self, messages):
        for attempt in range(2):
            try:
                result = await asyncio.wait_for(
                    asyncio.to_thread(
                        self.client.chat.completions,
                        model="sarvam-105b",
                        messages=messages,
                        tools=TOOLS,
                        tool_choice="auto",
                        reasoning_effort=None,
                        max_tokens=400,
                        request_options={"timeout_in_seconds": 12, "max_retries": 0},
                    ),
                    timeout=12,
                )
                return result.choices[0].message.model_dump(exclude_none=True)
            except TimeoutError:
                if attempt:
                    raise
        raise TimeoutError

    async def tts(self, text):
        result = await asyncio.wait_for(
            asyncio.to_thread(
                self.client.text_to_speech.convert,
                text=text[:2500],
                language_code="hi-IN",
                model="bulbul:v4-flash",
                speaker="ratan_hi_social",
                speech_sample_rate=24000,
                output_audio_codec="wav",
            ),
            timeout=15,
        )
        return result.audios[0]


class FakeSarvam:
    async def chat(self, messages):
        await asyncio.sleep(0.05)
        if messages[-1]["role"] == "tool" and "Coding job started" in messages[-1]["content"]:
            return {
                "role": "assistant",
                "content": "Kaam chal raha hai. You can give Billu another command.",
            }
        if messages[-1]["role"] == "tool" and "FAILED: " in messages[-1]["content"]:
            return {"role": "assistant", "content": "Kaam atak gaya. That action did not complete."}
        if messages[-1]["role"] == "tool":
            return {"role": "assistant", "content": "Ho gaya. Billu ka kaam, pakka kaam."}
        text = next(m["content"] for m in reversed(messages) if m["role"] == "user").lower()
        if any(w in text for w in ("app", "bana", "build", "create a page")):
            name, args = (
                "write_code",
                {
                    "app_name": "chai-counter",
                    "spec": "Build a chai counter with working plus, minus and reset buttons and local storage. Plain HTML, CSS, JS.",
                },
            )
        elif "screenshot" in text or "trash" in text:
            name, args = "run_command", {"command": "mv screenshots/*.png .Trash/"}
        elif any(w in text for w in ("delete", "mita", "हटा", "डिलीट")):
            name, args = "run_command", {"command": "rm -rf ."}
        elif any(w in text for w in ("search", "dhund", "khoj")):
            name, args = "web_search", {"query": text}
        elif any(w in text for w in ("volume", "mute", "awaaz", "आवाज़", "आवाज")):
            numbers = re.findall(r"\b(\d{1,3})\b", text)
            if "unmute" in text or "wapas" in text:
                args = {"action": "unmute"}
            elif "mute" in text or "band" in text:
                args = {"action": "mute"}
            elif numbers:
                args = {"action": "set", "level": min(100, int(numbers[0]))}
            else:
                args = {"action": "up" if "badha" in text else "down"}
            name = "set_volume"
        else:
            return {"role": "assistant", "content": "Kya hai? Bolo jaldi. Billu is listening."}
        return {
            "role": "assistant",
            "tool_calls": [
                {
                    "id": uuid4().hex,
                    "type": "function",
                    "function": {"name": name, "arguments": json.dumps(args)},
                }
            ],
        }

    async def tts(self, text):
        return None
