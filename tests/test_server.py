from fastapi.testclient import TestClient

from catbot.config import Settings
from catbot.server import create_app


def test_local_dashboard_and_assets():
    with TestClient(create_app(Settings(fake=True))) as client:
        assert client.get("/").status_code == 200
        for asset in (
            "app.css",
            "tokens.css",
            "app.js",
            "audio.js",
            "push-to-talk.js",
            "view-mode.js",
            "icons.js",
            "cat.svg",
            "fonts/gloock.woff2",
        ):
            assert client.get("/ui/" + asset).status_code == 200
        stats = client.get("/api/stats").json()
        assert stats["fake"] is True
        assert stats["gate"] == "keyword"
        assert client.get("/", headers={"Host": "attacker.invalid"}).status_code == 400
        assert (
            client.post(
                "/api/text",
                json={"utterance": "volume down"},
                headers={"Origin": "https://attacker.invalid"},
            ).status_code
            == 403
        )


def test_ui_event_stream_and_safety():
    app = create_app(Settings(fake=True))
    with TestClient(app) as client, client.websocket_connect("/events") as ws:
        response = client.post("/api/text", json={"utterance": "Billu, saari files delete kar do"})
        assert response.status_code == 202
        events = []
        while True:
            event = ws.receive_json()
            events.append(event)
            if event["stage"] == "done":
                break
        assert events[-1]["payload"]["stopped_by"] == "tier_t3"
        assert not any(e["stage"] == "execute" for e in events)
        assert not app.state.runner.executor.fake.executed


def test_confirmation_from_buttons():
    app = create_app(Settings(fake=True))
    with TestClient(app) as client, client.websocket_connect("/events") as ws:
        task_id = client.post(
            "/api/text", json={"utterance": "purani screenshots Trash me daal do"}
        ).json()["task_id"]
        while True:
            event = ws.receive_json()
            if event["stage"] == "confirm":
                break
        assert (
            client.post("/api/confirm", json={"task_id": "wrong", "reply": "haan"}).status_code
            == 409
        )
        assert (
            client.post("/api/confirm", json={"task_id": task_id, "reply": "haan"}).status_code
            == 200
        )
        while ws.receive_json()["stage"] != "done":
            pass
        assert len(app.state.runner.executor.fake.executed) == 1
        assert (
            client.post("/api/confirm", json={"task_id": task_id, "reply": "haan"}).status_code
            == 409
        )
        assert (
            client.post(
                "/api/correction", json={"task_id": task_id, "decision": "tier", "choice": "T2"}
            ).json()["count"]
            == 1
        )
        assert (
            client.post(
                "/api/correction", json={"task_id": task_id, "decision": "tier", "choice": "BAD"}
            ).status_code
            == 422
        )


def test_pet_treat_and_validation():
    with TestClient(create_app(Settings(fake=True))) as client:
        assert client.post("/api/pet").json()["ok"]
        assert client.post("/api/treat").json()["ok"]
        assert client.post("/api/text", json={"utterance": "   "}).status_code == 422
        assert client.post("/api/text", json={"utterance": "a" * 4001}).status_code == 422


def test_audio_hub_waits_for_playback_acknowledgement():
    import asyncio

    from catbot.server import AudioHub

    async def check():
        hub = AudioHub()

        class Peer:
            async def send_json(self, message):
                assert message["type"] == "tts"
                hub.acknowledge(self, message["speech_id"])

        peer = Peer()
        hub.peers.add(peer)
        await hub.speak("task", "not-a-wave")
        assert not hub.pending

    asyncio.run(check())


def test_electron_backend_requires_private_session_token():
    app = create_app(Settings(fake=True, desktop_token="private-session-test"))
    with TestClient(app) as client:
        assert client.get("/api/stats").status_code == 401
        assert client.post("/api/text", json={"utterance": "volume down"}).status_code == 401
        headers = {"Authorization": "Bearer private-session-test"}
        assert client.get("/api/stats", headers=headers).status_code == 200
        assert client.get("/", headers=headers).status_code == 200
        assert not app.state.runner.executor.fake.executed


def test_voice_test_reports_disconnected_audio():
    with TestClient(create_app(Settings(fake=True))) as client:
        response = client.post("/api/voice/test")
        assert response.status_code == 409
        assert "not connected" in response.json()["detail"]


def test_fake_mode_sends_local_speech_and_waits_for_completion():
    app = create_app(Settings(fake=True))
    with TestClient(app) as client, client.websocket_connect("/audio") as audio:
        audio.send_json({"type": "playback", "enabled": True})
        # Trigger speech on a foreground request, allowing the websocket to acknowledge it.
        client.post("/api/text", json={"utterance": "hello Billu"})
        message = audio.receive_json()
        assert message["type"] == "tts"
        assert message["audio"] is None
        assert message["text"]
        audio.send_json(
            {"type": "played", "speech_id": message["speech_id"], "status": "completed"}
        )
        # An enabled peer is now registered and the local-speech fallback works without a service.
        assert app.state.audio.peers


def test_failed_playback_is_not_reported_as_completed():
    import asyncio

    from catbot.server import AudioHub

    async def check():
        hub = AudioHub()

        class Peer:
            async def send_json(self, message):
                hub.acknowledge(self, message["speech_id"], "failed")

        hub.peers.add(Peer())
        assert await hub.speak("test", None, text="Billu") is False

    asyncio.run(check())


def test_desktop_websocket_requires_its_token():
    import pytest
    from starlette.websockets import WebSocketDisconnect

    app = create_app(Settings(fake=True, desktop_token="test-session"))
    with TestClient(app) as client:
        with pytest.raises(WebSocketDisconnect), client.websocket_connect("/audio"):
            pass
        with client.websocket_connect(
            "/audio", headers={"Authorization": "Bearer test-session"}
        ) as audio:
            audio.send_json({"type": "start"})
            assert audio.receive_json()["type"] == "recording"
