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


def test_settings_repr_does_not_expose_keys():
    settings = Settings(sarvam_key="test-private-value", exa_key="test-other-private")
    assert "test-private" not in repr(settings)
    assert "test-other" not in repr(settings)


def test_event_log_redacts_nested_keys_and_user_codes():
    from catbot.events import EventBus

    bus = EventBus()
    bus.secrets = ("private-key-value",)
    event = bus.publish(
        "test",
        "think",
        args={"command": "echo private-key-value", "password": "private"},
        text="OTP 123456",
    )
    encoded = event.model_dump_json()
    assert "private-key-value" not in encoded
    assert "123456" not in encoded
    assert '"password":"private"' not in encoded
    assert "[redacted]" in encoded


async def test_slow_subscriber_is_bounded():
    from catbot.events import EventBus

    bus = EventBus()
    queue = bus.subscribe()
    for index in range(300):
        bus.publish("test", "result", summary=str(index))
    assert len(bus.history) == 100
    assert queue.qsize() == 200
    assert (await queue.get()).payload["summary"] == "100"
    bus.unsubscribe(queue)
