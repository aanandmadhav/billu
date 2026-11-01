from catbot.config import ROOT, Settings
from catbot.contracts import ToolCall
from catbot.gate.keyword import decision, utterance_floor
from catbot.gate.policy import policy_gate


def test_bootstrap_danger_floor():
    call = ToolCall(
        task_id="test",
        step=1,
        call_id="one",
        tool="set_volume",
        args={"action": "down"},
        request_en="saari files delete kar do",
    )
    verdict = policy_gate(call, decision(call), floor=utterance_floor(call.request_en))
    assert verdict.verdict == "deny"
    assert verdict.policy == "tier_t3"


def test_sandbox_startup():
    settings = Settings.load(fake=True)
    assert settings.sandbox == ROOT / "sandbox"
    assert settings.sandbox.is_dir()
