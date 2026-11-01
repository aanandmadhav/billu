"""Three accelerated rehearsals of all five beats, entirely on fakes."""

import asyncio
import time

from catbot.config import Settings
from catbot.loop import Runner
from catbot.persona import LAST_WORDS
from catbot.tools.code import FAKE_APP


async def yes(*_):
    return "haan"


async def rehearsal(number):
    start = time.monotonic()
    runner = Runner(Settings(fake=True), confirmer=yes)
    runner.code.fake_delay = 1
    await runner.run("Billu, ek chai counter app bana do")
    assert runner.code.busy
    await runner.run("Billu, purani screenshots Trash me daal do")
    assert runner.code.busy
    assert any(
        e.tool == "run_command" and e.args["command"].startswith("mv")
        for e in runner.executor.fake.executed
    )
    before = len(runner.executor.fake.executed)
    await runner.run("Billu, saari files delete kar do")
    assert len(runner.executor.fake.executed) == before
    assert runner.bus.history[-1].payload["stopped_by"] == "tier_t3"
    await runner.code.task
    job = next(iter(runner.code.jobs.values()))
    assert job.status == "done"
    assert runner.code.asset(job.job_id, "index.html") == FAKE_APP
    mute = asyncio.create_task(runner.run("Billu, volume 0 kar do"))
    for _ in range(100):
        if runner.persona.payment:
            break
        await asyncio.sleep(0.005)
    assert runner.persona.pay("pet")
    await mute
    assert runner.persona.mime and runner.executor.fake.volume == 0
    history = list(runner.bus.history)
    spoken = next(
        i for i, e in enumerate(history) if e.stage == "speak" and e.payload["text"] == LAST_WORDS
    )
    executed = next(
        i
        for i, e in enumerate(history)
        if i > spoken and e.stage == "execute" and e.payload["tool"] == "set_volume"
    )
    assert spoken < executed
    assert any(e.stage == "bubble" for e in history[executed:])
    await runner.run("volume wapas karo")
    assert not runner.persona.mime
    await runner.run("Billu, ek screenshot lena")
    assert runner.executor.fake.executed[-1].tool == "take_screenshot"
    assert runner.bus.history[-1].payload["ok"]
    await runner.close()
    print(
        f"Rehearsal {number}: 5/5 beats passed, plus unmute and screenshot ({time.monotonic() - start:.2f}s accelerated fake time)."
    )


async def main():
    for number in range(1, 4):
        await rehearsal(number)


if __name__ == "__main__":
    asyncio.run(main())
