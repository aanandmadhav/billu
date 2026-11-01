"""Live voice round trip using synthesized audio, without microphone access."""

import asyncio
import base64
import io
import wave

import numpy as np

from catbot.config import Settings
from scripts.smoke import permit


async def main():
    from sarvamai import (
        AsyncSarvamAI,
        RealtimeAudioInput,
        RealtimeEnd,
        RealtimeSpeechEnd,
        RealtimeSpeechStart,
        SarvamAI,
    )

    settings = Settings.load()
    permit("set_volume", {"action": "down"})
    response = await asyncio.to_thread(
        SarvamAI(api_subscription_key=settings.sarvam_key).text_to_speech.convert,
        text="बिल्लू, आवाज़ कम करो।",
        language_code="hi-IN",
        model="bulbul:v4-flash",
        speaker="ratan_hi_social",
        speech_sample_rate=24000,
        output_audio_codec="wav",
    )
    with wave.open(io.BytesIO(base64.b64decode(response.audios[0])), "rb") as audio:
        rate = audio.getframerate()
        samples = np.frombuffer(audio.readframes(audio.getnframes()), dtype="<i2").astype(
            np.float64
        )
    pcm = (
        np.interp(np.arange(0, len(samples), rate / 16000), np.arange(len(samples)), samples)
        .astype("<i2")
        .tobytes()
    )
    client = AsyncSarvamAI(api_subscription_key=settings.sarvam_key)
    async with client.speech_to_text_realtime_streaming.connect(
        language_code="auto",
        model="saaras:v3-realtime",
        stream_type="fast",
        endpointing="manual",
        encoding="linear16",
        sample_rate="16000",
    ) as socket:

        async def receive():
            async for event in socket:
                if hasattr(event, "model_dump"):
                    data = event.model_dump(exclude_none=True)
                else:
                    data = event
                print(data, flush=True)
                if isinstance(data, dict) and data.get("event") == "transcript.final":
                    return data

        receiver = asyncio.create_task(receive())
        await socket.send_realtime_speech_start(RealtimeSpeechStart())
        for start in range(0, len(pcm), 3200):
            frame = pcm[start : start + 3200].ljust(3200, b"\0")
            await socket.send_realtime_audio_input(
                RealtimeAudioInput(audio=base64.b64encode(frame).decode())
            )
            await asyncio.sleep(0.1)
        await socket.send_realtime_speech_end(RealtimeSpeechEnd())
        final = await asyncio.wait_for(receiver, timeout=10)
        assert final
        await socket.send_realtime_end(RealtimeEnd())
        print("VOICE ROUND TRIP PASSED", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
