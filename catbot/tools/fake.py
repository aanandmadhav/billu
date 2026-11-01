import asyncio

from catbot.contracts import ToolResult
from catbot.tools.volume import next_level


class FakeTools:
    """Deterministic in-memory tools. No desktop, network, Codex or file writes."""

    def __init__(self):
        self.volume = 50
        self.executed = []
        self.code_job = None

    async def run(self, call):
        self.executed.append(call.model_copy(deep=True))
        await asyncio.sleep(0.01)
        if call.tool == "set_volume":
            self.volume = next_level(self.volume, call.args["action"], call.args.get("level"))
            return ToolResult(
                ok=True,
                summary=f"Fake volume {self.volume}%",
                data={"level": self.volume, "muted": self.volume == 0},
            )
        if call.tool == "run_command":
            return ToolResult(
                ok=True,
                summary="Fake command completed inside sandbox/.",
                data={"stdout": "3 screenshots moved to sandbox/.Trash", "exit_code": 0},
            )
        if call.tool == "web_search":
            return ToolResult(
                ok=True,
                summary="Fake search: three chai references.",
                origin="web",
                data={
                    "results": [
                        {
                            "title": "Demo chai reference",
                            "url": "https://example.com",
                            "text": "Demo data only.",
                        }
                    ]
                },
            )
        return ToolResult(
            ok=True, summary="Fake coding job started.", origin="code", data={"job_id": "fake-job"}
        )
