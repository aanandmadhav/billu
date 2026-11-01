import os
import platform
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent


@dataclass
class Settings:
    fake: bool = False
    demo_tease: bool = True
    port: int = 8765
    sandbox: Path = ROOT / "sandbox"
    model_dir: Path = ROOT / "models/laya"
    sarvam_key: str = field(default="", repr=False)
    exa_key: str = field(default="", repr=False)
    desktop_token: str = field(default="", repr=False)
    capture_endpoint: str = field(default="", repr=False)
    capture_token: str = field(default="", repr=False)
    os_name: str = platform.system().lower()

    @classmethod
    def load(cls, fake: bool = False):
        load_dotenv(ROOT / ".env")
        sandbox = (ROOT / os.getenv("SANDBOX_DIR", "sandbox")).resolve()
        # The runtime workspace is always the repo's sandbox, never the source tree.
        required = ROOT / "sandbox"
        if required.is_symlink() or sandbox != required:
            raise ValueError("SANDBOX_DIR must be the repo-root sandbox directory")
        sandbox.mkdir(parents=True, exist_ok=True)
        return cls(
            fake=fake or os.getenv("CATBOT_FAKES", "0") == "1",
            demo_tease=os.getenv("DEMO_TEASE", "1") == "1",
            port=int(os.getenv("PORT", "8765")),
            sandbox=sandbox,
            model_dir=(ROOT / os.getenv("LAYA_MODEL_DIR", "models/laya")).resolve(),
            desktop_token=os.getenv("CATBOT_DESKTOP_TOKEN", ""),
            capture_endpoint=os.getenv("CATBOT_CAPTURE_ENDPOINT", ""),
            capture_token=os.getenv("CATBOT_CAPTURE_TOKEN", ""),
            sarvam_key=os.getenv("SARVAM_API_KEY", ""),
            exa_key=os.getenv("EXA_API_KEY", ""),
        )
