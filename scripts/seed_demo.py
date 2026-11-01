"""Create three synthetic old screenshots inside sandbox, through the gated executor."""

import argparse
import asyncio
import os
import struct
import zlib
from datetime import UTC, datetime

from catbot.config import Settings
from catbot.contracts import ToolCall, ToolResult
from catbot.events import EventBus
from catbot.gate.keyword import decision
from catbot.tools.executor import Executor
from catbot.tools.shell import confined_path


def png(index):
    def chunk(kind, data):
        return (
            struct.pack(">I", len(data))
            + kind
            + data
            + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)
        )

    width, height = 480, 300
    pixels = bytearray()
    for y in range(height):
        pixels.append(0)
        for x in range(width):
            if 30 < x < 450 and 35 < y < 265:
                color = (30 + index * 5, 42 + index * 5, 34 + index * 5)
                if (
                    60 < x < 310
                    and 70 < y < 90
                    or 60 < x < 390
                    and 120 < y < 130
                    or 60 < x < 250
                    and 160 < y < 170
                ):
                    color = (163, 189, 152)
            else:
                color = (12, 18, 14)
            pixels.extend(color)
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
        + chunk(b"tEXt", b"Description\0Synthetic Catbot demo screenshot. No real screen content.")
        + chunk(b"IDAT", zlib.compress(bytes(pixels)))
        + chunk(b"IEND", b"")
    )


class SeedWriter:
    def __init__(self, settings):
        self.settings = settings

    async def start(self, call, args):
        if self.settings.fake:
            return ToolResult(
                ok=True, summary="Fake seed: three in-memory screenshots. No files written."
            )
        screenshots = confined_path(self.settings.sandbox, "screenshots")
        trash = confined_path(self.settings.sandbox, ".Trash")
        screenshots.mkdir(exist_ok=True)
        trash.mkdir(exist_ok=True)
        files = []
        for i in range(1, 4):
            path = confined_path(self.settings.sandbox, f"screenshots/old-screenshot-{i:02}.png")
            if not path.exists():
                with path.open("xb") as output:
                    output.write(png(i))
                old = datetime(2024, 1, i, tzinfo=UTC).timestamp()
                os.utime(path, (old, old))
            files.append(str(path.relative_to(self.settings.sandbox)))
        return ToolResult(
            ok=True,
            summary="Three old demo screenshots ready in sandbox/screenshots/.",
            data={"files": files},
        )


async def main(fake=False):
    settings = Settings.load(fake)
    executor = Executor(settings, EventBus())
    # An operator-only deterministic write_code handler seeds fixture images, never source files.
    executor.code = SeedWriter(settings)
    call = ToolCall(
        task_id="demo-seed",
        step=1,
        call_id="seed",
        tool="write_code",
        args={
            "app_name": "screenshots",
            "spec": "Create three synthetic old PNG screenshots and a local .Trash folder inside sandbox only. Preserve existing files.",
        },
        request_en="Seed the three synthetic screenshot files requested for the Catbot demo",
    )
    result = await executor.execute(call, executor.authorize(call, decision(call)))
    print(result.summary)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--fake", action="store_true")
    asyncio.run(main(parser.parse_args().fake))
