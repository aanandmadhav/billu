"""Probe manual STT edge cases without microphone access or desktop actions."""

import asyncio
import base64

from catbot.config import Settings
from scripts.smoke import permit


async def main():
    from sarvamai import (
        AsyncSarvamAI,
        RealtimeAudioInput,
        RealtimeEnd,
        RealtimeSpeechEnd,
        RealtimeSpeechStart,
    )

    settings = Settings.load()
    permit("web_search", {"query": "Verify Sarvam STT protocol edge cases for the voice bug"})
    for count in (0, 1, 10):
        print("SILENT_FRAMES", count, flush=True)
        client = AsyncSarvamAI(api_subscription_key=settings.sarvam_key)
        async with client.speech_to_text_realtime_streaming.connect(
            language_code="auto",
            model="saaras:v3-realtime",
            stream_type="fast",
            endpointing="manual",
            encoding="linear16",
            sample_rate="16000",
        ) as ws:
            await ws.send_realtime_speech_start(RealtimeSpeechStart())
            for _ in range(count):
                await ws.send_realtime_audio_input(
                    RealtimeAudioInput(audio=base64.b64encode(b"\0" * 3200).decode())
                )
                await asyncio.sleep(0.1)
            await ws.send_realtime_speech_end(RealtimeSpeechEnd())
            try:
                async with asyncio.timeout(4):
                    async for event in ws:
                        data = (
                            event.model_dump(exclude_none=True)
                            if hasattr(event, "model_dump")
                            else event
                        )
                        if isinstance(data, dict):
                            # Print only structured protocol fields, not request headers or credentials.
                            safe = {
                                key: data[key]
                                for key in (
                                    "event",
                                    "code",
                                    "message",
                                    "is_fatal",
                                    "text",
                                    "total_utterances",
                                )
                                if key in data
                            }
                            for key in ("message", "text"):
                                if key in safe:
                                    for secret in (settings.sarvam_key, settings.exa_key):
                                        if secret:
                                            safe[key] = safe[key].replace(secret, "[redacted]")
                            print(safe, flush=True)
                            if data.get("event") in ("transcript.final", "session.end", "error"):
                                break
            except TimeoutError:
                print("NO_FINAL_WITHIN_4S", flush=True)
            await ws.send_realtime_end(RealtimeEnd())


if __name__ == "__main__":
    asyncio.run(main())
