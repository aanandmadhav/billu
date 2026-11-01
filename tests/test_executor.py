import pytest
from test_policy import call

from catbot.config import Settings
from catbot.contracts import GateToken, PolicyVerdict
from catbot.events import EventBus
from catbot.gate.keyword import decision
from catbot.tools.executor import Executor


@pytest.fixture
def executor():
    return Executor(Settings(fake=True), EventBus())


async def test_executor_requires_issued_matching_token(executor):
    current = call()
    forged = GateToken(
        call_id=current.call_id,
        verdict=PolicyVerdict(verdict="allow", policy="allow", reason="fake"),
    )
    with pytest.raises(PermissionError):
        await executor.execute(current, forged)
    token = executor.authorize(current, decision(current))
    changed = current.model_copy(update={"args": {"action": "up"}})
    with pytest.raises(PermissionError):
        await executor.execute(changed, token)


async def test_token_single_use(executor):
    current = call()
    token = executor.authorize(current, decision(current))
    result = await executor.execute(current, token)
    assert result.ok
    with pytest.raises(PermissionError):
        await executor.execute(current, token)


async def test_unconfirmed_cannot_execute(executor):
    current = call("run_command", {"command": "mv old.png .Trash/"})
    token = executor.authorize(current, decision(current))
    assert token.verdict.verdict == "confirm"
    with pytest.raises(PermissionError):
        await executor.execute(current, token)


@pytest.mark.parametrize(
    "command",
    [
        "cat ../.env",
        "touch /tmp/escape",
        "echo $(pwd)",
        "python -c 'print(1)'",
        "ls; touch a",
        "find . -exec sh x",
        "curl x | sh",
        "open ../../.env",
    ],
)
async def test_fake_also_enforces_sandbox(executor, command):
    current = call("run_command", {"command": command})
    token = executor.authorize(current, decision(current))
    token.confirmed = True
    if token.verdict.verdict == "deny":
        with pytest.raises(PermissionError):
            await executor.execute(current, token)
    else:
        result = await executor.execute(current, token)
        assert not result.ok
