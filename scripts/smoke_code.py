"""Gated real background app probe; no speech API or system volume changes."""

import asyncio
import time
from uuid import uuid4

from catbot.config import Settings
from catbot.loop import Runner
from catbot.sarvam import FakeSarvam


async def main():
    settings = Settings.load()
    settings.fake = False
    settings.demo_tease = False
    runner = Runner(settings, brain=FakeSarvam())
    start = time.monotonic()
    # A unique name preserves existing demo apps instead of replacing their files.
    name = "chai-probe-" + uuid4().hex[:8]
    from catbot.contracts import ToolCall
    from catbot.gate.keyword import decision

    call = ToolCall(
        task_id="p3-live",
        step=1,
        call_id=uuid4().hex,
        tool="write_code",
        args={
            "app_name": name,
            "spec": "Create a compact attractive chai counter. index.html with inline CSS and JS only. Large count, plus/minus and Reset buttons, every button works. No dependencies, no network. Finish in one file.",
        },
        request_en="Build and open a small local chai counter app for the Catbot live smoke test",
    )
    token = runner.executor.authorize(call, decision(call))
    result = await runner.executor.execute(call, token)
    print(result.model_dump_json(), flush=True)
    await runner.code.task
    job = next(iter(runner.code.jobs.values()))
    print(
        {
            "status": job.status,
            "files": job.files,
            "seconds": round(time.monotonic() - start, 2),
            "app": str(job.directory),
        },
        flush=True,
    )
    assert job.status == "done"
    assert any(e.stage == "gate" and e.payload.get("follow_up") for e in runner.bus.history)
    await runner.close()


if __name__ == "__main__":
    asyncio.run(main())
