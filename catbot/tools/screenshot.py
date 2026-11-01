"""One main-display PNG, with no model-selected executable, flags or output path."""

import struct
from urllib.parse import urlsplit
from uuid import uuid4

import httpx

from catbot.contracts import ToolResult
from catbot.tools.shell import bounded_process, confined_path, scrubbed_env


class ScreenshotTool:
    def __init__(self, settings):
        self.settings = settings

    async def __call__(self, _args):
        if self.settings.os_name != "darwin" and not self.settings.capture_endpoint:
            return ToolResult(ok=False, summary="Screenshot capture currently supports macOS only.")
        root = self.settings.sandbox
        directory = confined_path(root, "captures")
        directory.mkdir(exist_ok=True)
        capture_id = uuid4().hex
        target = confined_path(root, f"captures/{capture_id}.png")
        # Reserve a unique file, never replace an existing user file.
        with target.open("xb"):
            pass
        complete = False
        try:
            if self.settings.capture_endpoint:
                endpoint = urlsplit(self.settings.capture_endpoint)
                if (
                    endpoint.scheme != "http"
                    or endpoint.hostname != "127.0.0.1"
                    or not endpoint.port
                    or endpoint.path != "/capture"
                    or endpoint.query
                    or endpoint.fragment
                    or endpoint.username
                    or not self.settings.capture_token
                ):
                    raise ValueError("Invalid local screenshot bridge.")
                async with (
                    httpx.AsyncClient(timeout=15, trust_env=False) as client,
                    client.stream(
                        "POST",
                        self.settings.capture_endpoint,
                        headers={"Authorization": "Bearer " + self.settings.capture_token},
                    ) as response,
                ):
                    code = 0 if response.status_code == 200 else 1
                    if not code:
                        size = 0
                        with target.open("wb") as image:
                            async for block in response.aiter_bytes():
                                size += len(block)
                                if size > 50 * 1024 * 1024:
                                    raise ValueError(
                                        "Screenshot exceeded the local image size limit."
                                    )
                                image.write(block)
            else:
                code, _, _ = await bounded_process(
                    ["/usr/sbin/screencapture", "-x", "-m", "-t", "png", str(target)],
                    cwd=root,
                    env=scrubbed_env(root),
                    timeout=15,
                )
            if code:
                return ToolResult(
                    ok=False,
                    summary="Screen capture failed. In Full dashboard, open Permissions → Enable screenshots. Allow Catbot in Screen & System Audio Recording, then restart Catbot and try again.",
                    data={"error": "screen_capture_failed"},
                )
            with target.open("rb") as image:
                header = image.read(24)
            if len(header) < 24 or header[:8] != b"\x89PNG\r\n\x1a\n" or header[12:16] != b"IHDR":
                return ToolResult(ok=False, summary="Screen capture did not produce a valid PNG.")
            width, height = struct.unpack(">II", header[16:24])
            if not width or not height:
                return ToolResult(ok=False, summary="Screen capture returned an empty image.")
            complete = True
            return ToolResult(
                ok=True,
                summary=f"Billu saved the screenshot to sandbox/captures/{capture_id}.png.",
                data={
                    "capture_id": capture_id,
                    "path": f"sandbox/captures/{capture_id}.png",
                    "url": f"/captures/{capture_id}.png",
                    "width": width,
                    "height": height,
                },
            )
        except (TimeoutError, httpx.HTTPError):
            return ToolResult(
                ok=False,
                summary="Screen capture timed out. Check Catbot's Screen Recording permission and try again.",
            )
        finally:
            if not complete:
                target.unlink(missing_ok=True)
