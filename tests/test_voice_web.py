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


@pytest.mark.parametrize(
    "frames,code", [(0, "no_audio"), (1, "silent_input"), (10, "silent_input")]
)
async def test_empty_or_silent_recording_never_connects_to_sarvam(monkeypatch, frames, code):
    import sarvamai

    from catbot.sarvam import FakeSarvam

    calls = []

    def forbidden(**_):
        calls.append(True)
        raise AssertionError("An empty recording must not open Sarvam")

    monkeypatch.setattr(sarvamai, "AsyncSarvamAI", forbidden)
    runner = Runner(Settings(fake=False), brain=FakeSarvam())
    messages = []

    async def notify(message):
        messages.append(message)

    session = VoiceSession(runner, notify)
    session.start()
    for _ in range(frames):
        await session.feed(b"\0" * 3200)
    await session.finish()
    assert not calls
    assert messages[-1]["code"] == code
    assert messages[-1]["stop_recording"] is True
    assert not runner.executor.fake.executed


@pytest.mark.parametrize(
    "event,expected",
    [
        (
            {"event": "error", "code": "transcriber_error", "is_fatal": False},
            "transcription_failed",
        ),
        ({"event": "error", "code": "rate_limit_exceeded", "is_fatal": True}, "rate_limit"),
        ({"event": "error", "code": "unauthorized", "is_fatal": True}, "authentication"),
        ({"event": "session.end"}, "no_transcript"),
        ({"event": "transcript.final", "text": ""}, "no_speech"),
    ],
)
async def test_stt_events_produce_actionable_errors_and_never_execute(monkeypatch, event, expected):
    import asyncio

    import sarvamai

    from catbot.sarvam import FakeSarvam

    class Socket:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *_):
            pass

        async def send_realtime_speech_start(self, _):
            pass

        async def send_realtime_audio_input(self, _):
            pass

        async def send_realtime_speech_end(self, _):
            pass

        async def send_realtime_end(self, _):
            pass

        async def __aiter__(self):
            yield {"event": "session.begin"}
            await asyncio.sleep(0)
            yield event

    class Client:
        def __init__(self, **_):
            self.speech_to_text_realtime_streaming = self

        def connect(self, **_):
            return Socket()

    monkeypatch.setattr(sarvamai, "AsyncSarvamAI", Client)
    runner = Runner(Settings(fake=False), brain=FakeSarvam())
    messages = []

    async def notify(message):
        messages.append(message)

    session = VoiceSession(runner, notify)
    session.start()
    await session.feed(b"\1\0" * 1600)
    await session.finish()
    assert messages[-1]["code"] == expected
    assert "RuntimeError" not in messages[-1]["message"]
    assert not runner.executor.fake.executed


async def test_initial_silence_keeps_only_short_preroll():
    runner = Runner(Settings(fake=True))

    async def notify(_):
        pass

    session = VoiceSession(runner, notify)
    for _ in range(5):
        await session.feed(b"\0" * 3200)
    await session.feed(b"\1\0" * 1600)
    initial = await session._initial_audio()
    assert len(initial) == 3
    assert initial[-1] == b"\1\0" * 1600
