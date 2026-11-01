import asyncio

from catbot.contracts import ToolResult
from catbot.tools.shell import bounded_process, scrubbed_env


def next_level(current, action, level=None):
    if action == "mute":
        return 0
    if action == "up":
        return min(100, current + 10)
    if action == "down":
        return max(0, current - 10)
    if action == "unmute":
        return max(current, 50)
    return level


class VolumeTool:
    def __init__(self, settings):
        self.settings = settings
        self.last_nonzero = 50

    async def __call__(self, args):
        if self.settings.os_name == "windows":
            return await asyncio.to_thread(self._windows, args)
        if self.settings.os_name != "darwin":
            return ToolResult(ok=False, summary="System volume is supported on macOS and Windows.")
        code, stdout, _ = await bounded_process(
            ["/usr/bin/osascript", "-e", "output volume of (get volume settings)"],
            cwd=self.settings.sandbox,
            env=scrubbed_env(self.settings.sandbox),
        )
        if code:
            return ToolResult(ok=False, summary="Could not read the system volume.")
        current = int(stdout.strip())
        if current > 0:
            self.last_nonzero = current
        level = next_level(current, args["action"], args.get("level"))
        if args["action"] == "unmute":
            level = self.last_nonzero
        script = f"set volume output volume {level}\nset volume output muted {'true' if level == 0 else 'false'}"
        code, _, _ = await bounded_process(
            ["/usr/bin/osascript", "-e", script],
            cwd=self.settings.sandbox,
            env=scrubbed_env(self.settings.sandbox),
        )
        return ToolResult(
            ok=code == 0,
            summary=f"Volume {level}%" if code == 0 else "Volume change failed.",
            data={"level": level, "muted": level == 0},
        )

    def _windows(self, args):
        try:
            import comtypes
            from pycaw.pycaw import AudioUtilities

            comtypes.CoInitialize()
            try:
                volume = AudioUtilities.GetSpeakers().EndpointVolume
                current = round(volume.GetMasterVolumeLevelScalar() * 100)
                if current > 0:
                    self.last_nonzero = current
                level = next_level(current, args["action"], args.get("level"))
                if args["action"] == "unmute":
                    level = self.last_nonzero
                volume.SetMasterVolumeLevelScalar(level / 100, None)
                volume.SetMute(level == 0, None)
                return ToolResult(
                    ok=True, summary=f"Volume {level}%", data={"level": level, "muted": level == 0}
                )
            finally:
                comtypes.CoUninitialize()
        except ImportError:
            return ToolResult(
                ok=False, summary="Install Catbot with the windows extra for system volume."
            )
