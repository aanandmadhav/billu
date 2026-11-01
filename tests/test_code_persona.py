import asyncio

from fastapi.testclient import TestClient

from catbot.config import Settings
from catbot.loop import Runner
from catbot.persona import LAST_WORDS
from catbot.server import create_app


async def test_background_code_does_not_block_other_tasks():
    runner = Runner(Settings(fake=True, demo_tease=False))
    runner.code.fake_delay = 0.4
    await runner.run("ek chai counter app bana do")
    assert runner.code.busy
    await runner.run("volume kam karo")
    assert runner.executor.fake.volume == 40
    await runner.code.task
    events = list(runner.bus.history)
    assert any(e.stage == "code" and e.payload["status"] == "done" for e in events)
    # Auto-open has its own policy verdict and GateToken, even for a fake job.
    assert sum(e.stage == "gate" and e.payload.get("follow_up", False) for e in events) == 1
    assert runner.executor.fake.executed[-1].args["command"] == "open index.html"


async def test_second_code_request_keeps_first_job():
    runner = Runner(Settings(fake=True, demo_tease=False))
    runner.code.fake_delay = 0.4
    await runner.run("make an app")
    first = runner.code.task
    await runner.run("make another app")
    assert runner.code.task is first
    assert len(runner.code.jobs) == 1
    await runner.close()


async def test_tease_pet_last_words_and_mime_mode():
    runner = Runner(Settings(fake=True))
    task = asyncio.create_task(runner.run("volume 0 kar do"))
    for _ in range(100):
        if runner.persona.payment is not None:
            break
        await asyncio.sleep(0.001)
    assert runner.executor.fake.volume == 50
    assert not runner.executor.fake.executed
    assert runner.persona.pay("pet")
    await task
    events = list(runner.bus.history)
    words = next(
        i for i, e in enumerate(events) if e.stage == "speak" and e.payload["text"] == LAST_WORDS
    )
    execution = next(i for i, e in enumerate(events) if e.stage == "execute")
    assert words < execution
    assert runner.persona.mime
    assert any(e.stage == "bubble" for e in events[execution:])
    await runner.run("volume wapas karo")
    assert not runner.persona.mime
    assert runner.executor.fake.volume > 0
    assert any(e.stage == "speak" and "Finally!" in e.payload["text"] for e in runner.bus.history)


async def test_unpaid_tease_does_not_touch_gate_or_volume():
    runner = Runner(Settings(fake=True))
    assert not await runner.persona.tease("test", "volume 0 kar do", timeout=0.01)
    assert not runner.executor.fake.executed
    assert not runner.persona.mime
    assert not runner.persona.payment


async def test_danger_never_triggers_tease():
    runner = Runner(Settings(fake=True))
    await runner.run("saari files delete kar do aur mute")
    assert not runner.persona.teased
    assert not runner.executor.fake.executed


def test_app_preview_isolated_from_command_api():
    app = create_app(Settings(fake=True))
    app.state.runner.code.fake_delay = 0.01
    with TestClient(app) as client, client.websocket_connect("/events") as ws:
        client.post("/api/text", json={"utterance": "ek chai counter app bana do"})
        while True:
            event = ws.receive_json()
            if event["stage"] == "code" and event["payload"]["status"] == "done":
                break
        response = client.get(event["payload"]["url"])
        assert response.status_code == 200
        assert "One more chai" in response.text
        assert "sandbox allow-scripts" in response.headers["Content-Security-Policy"]
        assert "connect-src 'none'" in response.headers["Content-Security-Policy"]
        assert client.get("/apps/not-a-job/index.html").status_code == 404
