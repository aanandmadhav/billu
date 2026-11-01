import struct
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from catbot.config import Settings
from catbot.contracts import GateToken, PolicyVerdict, ToolCall
from catbot.events import EventBus
from catbot.gate.keyword import decision
from catbot.loop import Runner
from catbot.sarvam import FakeSarvam
from catbot.server import create_app
from catbot.tools.executor import Executor


def capture_call(args=None):
    return ToolCall(
        task_id="capture-test",
        step=1,
        call_id="shot",
        tool="take_screenshot",
        args=args or {},
        request_en="Take a screenshot of the main display",
    )


async def execute(executor, call=None):
    call = call or capture_call()
    token = executor.authorize(call, decision(call))
    assert token.verdict.verdict == "allow"
    return await executor.execute(call, token)


def png_header():
    return b"\x89PNG\r\n\x1a\n" + struct.pack(">I", 13) + b"IHDR" + struct.pack(">II", 640, 480)


async def test_screenshot_requires_issued_token_and_fake_never_reads_screen(tmp_path, monkeypatch):
    executor = Executor(Settings(fake=True, sandbox=tmp_path), EventBus())

    async def forbidden(*args, **kwargs):
        raise AssertionError("Fake mode accessed real screen")

    monkeypatch.setattr(executor, "screenshot", forbidden)
    call = capture_call()
    forged = GateToken(
        call_id=call.call_id,
        verdict=PolicyVerdict(verdict="allow", policy="allow", reason="forged"),
    )
    with pytest.raises(PermissionError):
        await executor.execute(call, forged)
    result = await execute(executor)
    assert result.ok and result.data["fake"]
    assert not list(tmp_path.iterdir())


async def test_screenshot_is_fixed_argv_and_confined_png(tmp_path, monkeypatch):
    async def capture(argv, **kwargs):
        assert argv[:5] == ["/usr/sbin/screencapture", "-x", "-m", "-t", "png"]
        target = Path(argv[-1])
        assert target.parent == tmp_path / "captures"
        assert kwargs["cwd"] == tmp_path
        target.write_bytes(png_header())
        return 0, "", ""

    monkeypatch.setattr("catbot.tools.screenshot.bounded_process", capture)
    executor = Executor(Settings(fake=False, sandbox=tmp_path, os_name="darwin"), EventBus())
    result = await execute(executor)
    assert result.ok
    assert (result.data["width"], result.data["height"]) == (640, 480)
    target = tmp_path / "captures" / (result.data["capture_id"] + ".png")
    assert target.is_file()
    assert result.data["url"] == f"/captures/{target.name}"


@pytest.mark.parametrize("failure", ["permission", "empty", "timeout"])
async def test_failed_capture_cleans_partial_and_reports_reason(tmp_path, monkeypatch, failure):
    async def capture(*args, **kwargs):
        if failure == "timeout":
            raise TimeoutError
        return (1 if failure == "permission" else 0), "", "private OS diagnostics"

    monkeypatch.setattr("catbot.tools.screenshot.bounded_process", capture)
    executor = Executor(Settings(fake=False, sandbox=tmp_path, os_name="darwin"), EventBus())
    result = await execute(executor)
    assert not result.ok
    assert "private OS diagnostics" not in result.summary
    assert not list((tmp_path / "captures").iterdir())


async def test_screenshot_rejects_model_paths_and_symlinked_directory(tmp_path, monkeypatch):
    async def forbidden(*args, **kwargs):
        raise AssertionError("Unexpected capture")

    monkeypatch.setattr("catbot.tools.screenshot.bounded_process", forbidden)
    executor = Executor(Settings(fake=False, sandbox=tmp_path, os_name="darwin"), EventBus())
    assert not (await execute(executor, capture_call({"path": "/tmp/escape.png"}))).ok
    (tmp_path / "captures").symlink_to(tmp_path.parent, target_is_directory=True)
    result = await execute(executor)
    assert not result.ok and "Symbolic links" in result.summary


async def test_capture_failure_stops_without_retries(tmp_path):
    runner = Runner(Settings(fake=True, sandbox=tmp_path))
    from catbot.contracts import ToolResult

    async def fail(call):
        return ToolResult(ok=False, summary="Screen permission required")

    runner.executor.fake.run = fail
    await runner.run("Billu screenshot lena")
    assert runner.bus.history[-1].payload["stopped_by"] == "screenshot_failed"
    assert sum(e.stage == "execute" for e in runner.bus.history) == 1
    await runner.close()


async def test_capture_preview_auth_and_symlink_protection(tmp_path, monkeypatch):
    async def capture(argv, **kwargs):
        Path(argv[-1]).write_bytes(png_header())
        return 0, "", ""

    monkeypatch.setattr("catbot.tools.screenshot.bounded_process", capture)
    executor = Executor(Settings(fake=False, sandbox=tmp_path, os_name="darwin"), EventBus())
    result = await execute(executor)
    runner = Runner(Settings(fake=True, sandbox=tmp_path), brain=FakeSarvam())
    app = create_app(
        Settings(fake=False, sandbox=tmp_path, desktop_token="test-session"), runner=runner
    )
    with TestClient(app) as client:
        url = result.data["url"]
        assert client.get(url).status_code == 401
        headers = {"Authorization": "Bearer test-session"}
        response = client.get(url, headers=headers)
        assert response.status_code == 200
        assert response.headers["content-type"] == "image/png"
        assert client.get("/captures/not-a-capture.png", headers=headers).status_code == 404
        target = tmp_path / "captures" / (result.data["capture_id"] + ".png")
        target.unlink()
        target.symlink_to(__file__)
        assert client.get(url, headers=headers).status_code == 404


async def test_electron_capture_transport_uses_only_private_loopback_endpoint(
    tmp_path, monkeypatch
):
    import httpx

    seen = []

    async def handle(request):
        seen.append(request)
        assert request.method == "POST"
        assert request.headers["authorization"] == "Bearer native-private-token"
        return httpx.Response(200, content=png_header())

    original_client = httpx.AsyncClient
    monkeypatch.setattr(
        "catbot.tools.screenshot.httpx.AsyncClient",
        lambda **kwargs: original_client(transport=httpx.MockTransport(handle), **kwargs),
    )
    executor = Executor(
        Settings(
            fake=False,
            sandbox=tmp_path,
            capture_endpoint="http://127.0.0.1:12345/capture",
            capture_token="native-private-token",
        ),
        EventBus(),
    )
    result = await execute(executor)
    assert result.ok and result.data["width"] == 640
    assert len(seen) == 1
    executor.settings.capture_endpoint = "https://example.com/capture"
    assert not (await execute(executor)).ok
    assert len(seen) == 1
