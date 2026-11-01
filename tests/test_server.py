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
