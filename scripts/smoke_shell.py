"""Exercise confined real filesystem commands with policy tokens; no source changes."""

import asyncio
from uuid import uuid4

from catbot.config import Settings
from catbot.contracts import ToolCall
from catbot.events import EventBus
from catbot.gate.keyword import decision
from catbot.tools.executor import Executor


async def main():
    settings = Settings.load()
    settings.fake = False
    executor = Executor(settings, EventBus())
    folder = "shell-probe-" + uuid4().hex[:8]
    commands = [
        f"mkdir {folder}",
        f"echo Billu > {folder}/old.txt",
        f"mv {folder}/old.txt {folder}/new.txt",
        f"cat {folder}/new.txt",
    ]
    for index, command in enumerate(commands, 1):
        call = ToolCall(
            task_id="shell-probe",
            step=index,
            call_id=str(index),
            tool="run_command",
            args={"command": command},
            request_en="Create and move an isolated disposable demo file inside sandbox for the requested build smoke test",
        )
        token = executor.authorize(call, decision(call))
        # This operator smoke explicitly approves its one T2 move of a newly created fixture.
        if token.verdict.verdict == "confirm":
            token.confirmed = True
        result = await executor.execute(call, token)
        assert result.ok, result.summary
    assert (settings.sandbox / folder / "new.txt").read_text().strip() == "Billu"
    print("Real sandbox shell: mkdir, echo redirect, confirmed move and read passed.")


if __name__ == "__main__":
    asyncio.run(main())
