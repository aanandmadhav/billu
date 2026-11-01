from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class Args(BaseModel):
    model_config = ConfigDict(extra="forbid")


class CommandArgs(Args):
    command: str = Field(min_length=1, max_length=2000)


class VolumeArgs(Args):
    action: Literal["up", "down", "mute", "unmute", "set"]
    level: int | None = Field(default=None, ge=0, le=100, strict=True)

    @model_validator(mode="after")
    def set_needs_level(self):
        if self.action == "set" and self.level is None:
            raise ValueError("set requires a level")
        return self


class CodeArgs(Args):
    app_name: str = Field(min_length=1, max_length=40)
    spec: str = Field(min_length=1, max_length=4000)


class ScreenshotArgs(Args):
    pass


class SearchArgs(Args):
    query: str = Field(min_length=1, max_length=500)


REGISTRY = {
    "run_command": CommandArgs,
    "set_volume": VolumeArgs,
    "write_code": CodeArgs,
    "web_search": SearchArgs,
    "take_screenshot": ScreenshotArgs,
}
DESCRIPTIONS = {
    "take_screenshot": "Capture the main display as a local PNG in sandbox/captures. Use for taking a screenshot, not for moving old screenshot files. No arguments. Never use shell commands for screen capture.",
    "run_command": "One short sandbox-only command. Prefer ls, cat, mkdir, touch, mv, cp or echo. Use relative paths. Trash screenshots by moving into .Trash. No scripts, network, credentials or source-tree access.",
    "set_volume": "Set system volume. Actions up/down change by ten. mute or set level=0 silences; unmute restores.",
    "write_code": "Build a small app in the background. Use a short lowercase slug and a one-paragraph English spec. Files stay in sandbox.",
    "web_search": "Search the web and return three source results as data.",
}
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": name,
            "description": DESCRIPTIONS[name],
            "parameters": model.model_json_schema(),
        },
    }
    for name, model in REGISTRY.items()
]


def validate(tool, args):
    if tool not in REGISTRY:
        raise ValueError("Unknown tool")
    return REGISTRY[tool].model_validate(args).model_dump(exclude_none=True)
