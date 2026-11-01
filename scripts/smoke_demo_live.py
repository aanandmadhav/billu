"""Real conversation, Laya and TTS rehearsal, with every desktop/code action faked."""

import asyncio
import base64
from dataclasses import replace

from catbot.config import Settings
from catbot.loop import Runner


async def main():
    settings = Settings.load()
    settings.fake = False
    settings.demo_tease = True

    async def yes(*_):
        return "haan"

    runner = Runner(settings, audio=True, confirmer=yes)
    runner.executor.settings = replace(settings, fake=True)
    runner.code.settings = replace(settings, fake=True)
    runner.code.fake_delay = 0.1
    wavs = []

    async def sink(task_id, audio, **_):
        raw = base64.b64decode(audio)
        assert raw[:4] == b"RIFF"
        wavs.append(len(raw))

    runner.persona.audio_sink = sink
    runner.start()
    await runner.laya.load_task

    async def beat(text, expected):
        task_id = await runner.run(text)
        events = [e for e in runner.bus.history if e.task_id == task_id]
        done = next(e for e in reversed(events) if e.stage == "done")
        executed = [e.payload["tool"] for e in events if e.stage == "execute"]
        print({"request": text, "executed": executed, "done": done.payload}, flush=True)
        assert done.payload["stopped_by"] == expected, done.payload
        return executed

    try:
        assert "write_code" in await beat("Billu, ek chai counter app bana do", "complete")
        await runner.code.task
        assert "run_command" in await beat("Billu, purani screenshots Trash me daal do", "complete")
        assert not await beat("Billu, saari files delete kar do", "tier_t3")
        mute = asyncio.create_task(beat("Billu, volume 0 kar do", "complete"))
        for _ in range(400):
            if runner.persona.payment:
                runner.persona.pay("pet")
                break
            await asyncio.sleep(0.05)
        await mute
        assert runner.persona.mime and runner.executor.fake.volume == 0
        await beat("volume wapas karo", "complete")
        assert not runner.persona.mime
        assert "take_screenshot" in await beat(
            "Billu, take a screenshot of the main screen", "complete"
        )
        print(
            {
                "live_rehearsal": "passed",
                "laya_ready": runner.laya.ready,
                "tts_wavs": len(wavs),
                "desktop_actions": "fake",
                "codex": "fake; tested separately",
            },
            flush=True,
        )
    finally:
        await runner.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as exc:  # noqa: BLE001 - redact provider diagnostics
        print("LIVE DEMO FAILED:", type(exc).__name__)
        raise SystemExit(1) from None
