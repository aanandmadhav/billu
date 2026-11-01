"""Real STT -> real Sarvam/Laya -> fake volume -> real TTS. No microphone or desktop."""

import asyncio
import base64
import io
import wave

import numpy as np

from catbot.config import Settings
from catbot.loop import Runner
from catbot.voice import VoiceSession
from scripts.smoke import permit


async def main():
    from sarvamai import SarvamAI

    settings = Settings.load()
    settings.fake = False
    settings.demo_tease = False
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
        values = np.frombuffer(audio.readframes(audio.getnframes()), dtype="<i2").astype(np.float64)
    pcm = (
        np.interp(np.arange(0, len(values), rate / 16000), np.arange(len(values)), values)
        .astype("<i2")
        .tobytes()
    )
    runner = Runner(settings, audio=True)
    # Only the desktop executor uses fakes; STT, chat, Laya and TTS remain real.
    runner.executor.settings = Settings(fake=True)
    spoken = []

    async def sink(task_id, audio, **_):
        raw = base64.b64decode(audio)
        assert raw[:4] == b"RIFF"
        spoken.append(len(raw))

    runner.persona.audio_sink = sink
    runner.start()
    await runner.laya.load_task

    async def notify(message):
        print(message, flush=True)

    session = VoiceSession(runner, notify)
    session.start()
    for i in range(0, len(pcm), 3200):
        await session.feed(pcm[i : i + 3200].ljust(3200, b"\0"))
        await asyncio.sleep(0.1)
    await session.finish()
    if runner.background:
        await asyncio.gather(*runner.background)
    for event in runner.bus.history:
        if event.stage in {"listen", "risk", "gate", "execute", "speak", "done"} and (
            event.stage != "listen" or "final" in event.payload
        ):
            print(event.model_dump_json(), flush=True)
    print({"fake_volume": runner.executor.fake.volume, "spoken_wav_bytes": spoken}, flush=True)
    assert runner.executor.fake.volume == 40
    assert spoken
    await runner.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as exc:  # noqa: BLE001 - redact provider diagnostics
        print("VOICE PIPELINE FAILED:", type(exc).__name__)
        raise SystemExit(1) from None
