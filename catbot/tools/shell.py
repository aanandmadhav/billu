"""Small, fail-closed command grammar; cwd alone is not a sandbox.

Only fixed OS executables, confined paths and known inert flags are accepted.
No shell expansions, interpreters, links, startup files, pipes or environment assignments.
"""

import asyncio
import glob
import os
import shlex
from pathlib import Path

from catbot.contracts import ToolResult

READ_FLAGS = {"-l", "-a", "-la", "-al", "-h", "-lh", "-lah", "-1"}
COMMANDS = {
    "ls": ("/bin/ls", READ_FLAGS),
    "pwd": ("/bin/pwd", set()),
    "cat": ("/bin/cat", {"-n"}),
    "head": ("/usr/bin/head", set()),
    "tail": ("/usr/bin/tail", set()),
    "wc": ("/usr/bin/wc", {"-l", "-w", "-c"}),
    "mkdir": ("/bin/mkdir", {"-p"}),
    "touch": ("/usr/bin/touch", set()),
    "mv": ("/bin/mv", {"-n"}),
    "cp": ("/bin/cp", {"-n"}),
    "rm": ("/bin/rm", {"-f"}),
    "open": ("/usr/bin/open", set()),
    "echo": ("/bin/echo", set()),
}


def confined_path(root: Path, value: str):
    root = root.resolve()
    path = Path(value)
    candidate = path if path.is_absolute() else root / path
    # Reject symlinks even if their current targets happen to remain inside.
    for part in (candidate, *candidate.parents):
        if part == root.parent:
            break
        if part.is_symlink():
            raise ValueError("Symbolic links cannot be used by Billu.")
    resolved = candidate.resolve()
    if not resolved.is_relative_to(root):
        raise ValueError("Billu only works inside sandbox/.")
    if any(
        p.startswith(".env") or p in {".git", ".ssh", ".aws"}
        for p in resolved.relative_to(root).parts
    ):
        raise ValueError("Credential and repository internals are off limits.")
    return resolved


def prepare(command: str, root: Path, *, virtual=False):
    if any(char in command for char in ("$", "`", "\n", "\r", "\x00", "\\", "~")):
        raise ValueError("Shell substitutions and escapes are not supported.")
    lexer = shlex.shlex(command, posix=True, punctuation_chars=";&|<>")
    lexer.whitespace_split = True
    lexer.commenters = ""
    words = list(lexer)
    # Chaining is deliberately unsupported. It would combine separate safety decisions.
    if any(w in {";", "&&", "||", "|", "&", "<", ">>", "&>"} for w in words):
        raise ValueError("Ask for one sandbox action at a time.")
    if not words:
        raise ValueError("Empty command")
    name = words.pop(0)
    if name == "start":
        name = "open"
    if name not in COMMANDS:
        raise ValueError("This command is outside Billu's sandbox command set.")
    executable, flags = COMMANDS[name]
    output = None
    if ">" in words:
        i = words.index(">")
        if name != "echo" or i != len(words) - 2:
            raise ValueError("Only echo text > relative-file is supported.")
        output = confined_path(root, words[-1])
        words = words[:i]
    argv = [executable]
    for word in words:
        if word.startswith("-"):
            if word not in flags:
                raise ValueError("Unsupported command option.")
            argv.append(word)
        elif name == "echo":
            argv.append(word)
        else:
            # A glob is expanded here, never by the shell; validate every resulting path.
            confined_path(root, word)
            matches = (
                glob.glob(str(root / word))
                if not virtual and any(c in word for c in "*?[")
                else [word]
            )
            if not matches:
                raise ValueError("No sandbox files match that path.")
            argv.extend(str(confined_path(root, match)) for match in matches)
    paths = [a for a in argv[1:] if not a.startswith("-")]
    if name in {"mv", "cp"} and len(paths) < 2:
        raise ValueError("Source and destination are required.")
    if name in {"touch", "mkdir", "rm", "open", "cat", "head", "tail"} and not paths:
        raise ValueError("A sandbox path is required.")
    if name == "open" and any(Path(p).suffix.lower() != ".html" for p in paths):
        raise ValueError("Billu opens only local HTML apps.")
    if name in {"ls", "wc"} and not paths:
        argv.append(str(root.resolve()))
    return argv, output


def scrubbed_env(root):
    # An allowlist also removes service keys, application startup hooks and inherited proxies.
    return {
        "PATH": "/usr/bin:/bin:/usr/sbin:/sbin",
        "HOME": str(root),
        "ZDOTDIR": str(root),
        "TMPDIR": str(root),
        "LANG": os.environ.get("LANG", "en_US.UTF-8"),
    }


async def bounded_process(argv, *, cwd, env=None, timeout=15, limit=8192):
    process = await asyncio.create_subprocess_exec(
        *argv,
        cwd=cwd,
        env=env,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        start_new_session=True,
    )

    async def drain(stream):
        kept = bytearray()
        while block := await stream.read(4096):
            if len(kept) < limit:
                kept.extend(block[: limit - len(kept)])
        return kept.decode("utf-8", errors="replace")

    try:
        async with asyncio.timeout(timeout):
            stdout, stderr = await asyncio.gather(drain(process.stdout), drain(process.stderr))
            await process.wait()
    except (TimeoutError, asyncio.CancelledError):
        if process.returncode is None:
            if os.name != "nt":
                import signal

                os.killpg(process.pid, signal.SIGKILL)
            else:
                process.kill()
        await process.wait()
        raise
    return process.returncode, stdout, stderr


class ShellTool:
    def __init__(self, settings):
        self.settings = settings

    def argv(self, args, cwd=None):
        root = cwd or self.settings.sandbox
        argv, output = prepare(args["command"], root, virtual=self.settings.fake)
        if os.name == "nt":
            # PowerShell receives a fixed, escaped invocation, never raw model text.
            binary = Path(argv[0]).name
            if binary == "open":
                binary = "Start-Process"
            command = "& " + " ".join("'" + a.replace("'", "''") + "'" for a in [binary, *argv[1:]])
            return ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", command], output
        return ["/bin/zsh", "-f", "-c", shlex.join(argv)], output

    async def __call__(self, args, *, cwd=None):
        root = cwd or self.settings.sandbox
        argv, output = self.argv(args, cwd=root)
        try:
            code, stdout, stderr = await bounded_process(argv, cwd=root, env=scrubbed_env(root))
            if output is not None:
                # Recheck immediately before writing, including all parent symlinks.
                output = confined_path(root, str(output))
                output.write_text(stdout)
            return ToolResult(
                ok=code == 0,
                summary=(stdout or stderr or f"exit {code}")[:8192],
                data={"exit_code": code, "stdout": stdout, "stderr": stderr},
            )
        except TimeoutError:
            return ToolResult(ok=False, summary="Command timed out after 15 seconds.")
