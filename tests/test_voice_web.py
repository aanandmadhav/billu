import pytest
from fastapi.testclient import TestClient
from test_policy import call

from catbot.config import Settings
from catbot.loop import Runner
from catbot.server import create_app
from catbot.voice import VoiceSession


def test_fake_voice_never_uses_real_services_and_routes_command():
    app = create_app(Settings(fake=True))
    with (
        TestClient(app) as client,
        client.websocket_connect("/events") as events,
        client.websocket_connect("/audio") as audio,
    ):
        audio.send_json({"type": "start"})
        assert audio.receive_json()["type"] == "recording"
        audio.send_bytes(b"\0" * 3200)
        audio.send_json({"type": "stop"})
        while events.receive_json()["stage"] != "done":
            pass
        assert app.state.runner.executor.fake.volume == 40


def test_spoken_reply_goes_to_waiting_confirmation():
    app = create_app(Settings(fake=True))
    with (
        TestClient(app) as client,
        client.websocket_connect("/events") as events,
        client.websocket_connect("/audio") as audio,
    ):
        task = client.post("/api/text", json={"utterance": "screenshots Trash me daal do"}).json()[
            "task_id"
        ]
        while events.receive_json()["stage"] != "confirm":
            pass
        audio.send_json({"type": "start"})
        assert audio.receive_json()["type"] == "recording"
        audio.send_json({"type": "stop"})
        while True:
            event = events.receive_json()
            if event["stage"] == "done":
                assert event["task_id"] == task
                break
        assert len(app.state.runner.executor.fake.executed) == 1


def test_invalid_audio_frame_cannot_start_an_action():
    app = create_app(Settings(fake=True))
    with TestClient(app) as client, client.websocket_connect("/audio") as audio:
        audio.send_json({"type": "start"})
        audio.receive_json()
        audio.send_bytes(b"bad audio")
        assert audio.receive_json()["type"] == "error"
        assert not app.state.runner.executor.fake.executed


async def test_voice_frame_limit_and_backpressure():
    runner = Runner(Settings(fake=True))

    async def notify(_):
        pass

    session = VoiceSession(runner, notify)
    for _ in range(64):
        await session.feed(b"\0" * 3200)
    with pytest.raises(ValueError, match="too slow"):
        await session.feed(b"\0" * 3200)
    session.received = 32000 * 30
    with pytest.raises(ValueError, match="30 seconds"):
        await session.feed(b"\0" * 3200)


async def test_fake_web_is_gated_and_labeled_data():
    runner = Runner(Settings(fake=True))
    current = call("web_search", {"query": "Delhi chai"})
    risk = await runner.laya.assess(current)
    result = await runner.executor.execute(current, runner.executor.authorize(current, risk))
    assert result.origin == "web"
    assert result.data["results"]
