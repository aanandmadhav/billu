import hashlib
import json

from pydantic import ValidationError

from catbot.contracts import GateToken, ToolResult
from catbot.gate.keyword import instruction_like
from catbot.gate.policy import policy_gate
from catbot.tools.fake import FakeTools
from catbot.tools.registry import validate
from catbot.tools.shell import ShellTool, confined_path
from catbot.tools.volume import VolumeTool


def fingerprint(call):
    return hashlib.sha256(call.model_dump_json().encode()).hexdigest()


class Executor:
    def __init__(self, settings, bus):
        self.settings = settings
        self.bus = bus
        self.fake = FakeTools()
        self.shell = ShellTool(settings)
        self.volume = VolumeTool(settings)
        self.code = None
        self.web = None
        self._issued = {}

    def authorize(self, call, risk, **context):
        token = GateToken(call_id=call.call_id, verdict=policy_gate(call, risk, **context))
        self._issued[id(token)] = (
            token,
            fingerprint(call),
            token.verdict.model_dump_json(),
            call.task_id,
        )
        return token

    def discard(self, token):
        self._issued.pop(id(token), None)

    def revoke_task(self, task_id):
        for identity, entry in tuple(self._issued.items()):
            if entry[3] == task_id:
                self._issued.pop(identity, None)

    async def execute(self, call, token, *, cwd=None):
        issued = self._issued.get(id(token))
        if (
            issued is None
            or issued[0] is not token
            or issued[1] != fingerprint(call)
            or issued[2] != token.verdict.model_dump_json()
            or token.call_id != call.call_id
            or not (
                token.verdict.verdict == "allow"
                or (token.verdict.verdict == "confirm" and token.confirmed)
            )
        ):
            raise PermissionError("A matching, unused policy GateToken is required.")
        self.discard(token)
        try:
            args = validate(call.tool, call.args)
            argv = []
            if cwd is not None:
                cwd = confined_path(self.settings.sandbox, str(cwd))
            if call.tool == "run_command":
                argv, _ = self.shell.argv(args, cwd=cwd)
            self.bus.publish(
                call.task_id, "execute", tool=call.tool, args=args, argv=argv, call_id=call.call_id
            )
            if call.tool == "write_code" and self.code is not None:
                result = await self.code.start(call, args)
            elif self.settings.fake:
                result = await self.fake.run(call.model_copy(update={"args": args}))
            elif call.tool == "run_command":
                result = await self.shell(args, cwd=cwd)
            elif call.tool == "set_volume":
                result = await self.volume(args)
            elif call.tool == "web_search" and self.web is not None:
                result = await self.web(args)
            else:
                result = ToolResult(ok=False, summary="This integration is not available yet.")
        except (ValueError, ValidationError, OSError) as exc:
            # Never reflect a service error, request headers, or environment back into logs.
            message = (
                str(exc)
                if isinstance(exc, ValueError) and not isinstance(exc, ValidationError)
                else "Tool arguments or local resources were invalid."
            )
            result = ToolResult(ok=False, summary=message[:400])
        self.bus.publish(
            call.task_id,
            "result",
            **result.model_dump(),
            provenance_flag=instruction_like(result.summary + json.dumps(result.data or {})),
        )
        return result
