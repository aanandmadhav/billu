"""One background Codex job at a time, confined to a fresh sandbox directory."""

import asyncio
import json
import os
import re
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from uuid import uuid4

from catbot.contracts import ToolCall, ToolResult
from catbot.gate.keyword import decision
from catbot.persona import CODE_BUSY, CODE_DONE, CODE_FAILED, CODE_PROGRESS, CODE_START
from catbot.tools.shell import confined_path

FAKE_APP = """<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Billu's chai counter</title><style>
*{box-sizing:border-box}body{margin:0;background:#17291e;color:#f1f5e9;font:18px/1.5 system-ui;min-height:100dvh;display:grid;place-items:center;padding:28px}main{width:min(100%,460px)}h1{font:400 42px/1.2 Georgia;margin:0 0 12px}p{color:#b9c8b5}output{display:block;font-size:120px;line-height:1.5;font-variant-numeric:tabular-nums}section{display:flex;gap:12px}button{min-height:54px;min-width:70px;padding:10px 24px;font:inherit;border:0;border-radius:8px;background:#d7e7ba;color:#17291e;cursor:pointer}button:hover{background:#f1f5e9}button:focus-visible{outline:3px solid #fff;outline-offset:4px}#reset{margin-left:auto;background:#314c38;color:#f1f5e9}small{display:block;margin-top:36px;color:#b9c8b5}</style><main><h1>Billu's chai counter.</h1><p>Ek aur cutting? Keep the count.</p><output id="count" aria-live="polite">0</output><section><button id="minus" aria-label="One less chai">−</button><button id="plus" aria-label="One more chai">+</button><button id="reset">Reset</button></section><small>Made by Billu · Catbot fake demo</small></main><script>
let count=0;try{count=Number(localStorage.getItem('billu-chai'))||0}catch{}const out=document.getElementById('count');function render(){out.textContent=count;try{localStorage.setItem('billu-chai',count)}catch{}}document.getElementById('plus').onclick=()=>{count++;render()};document.getElementById('minus').onclick=()=>{count=Math.max(0,count-1);render()};document.getElementById('reset').onclick=()=>{count=0;render()};render();</script></html>"""


@dataclass
class CodeJob:
    job_id: str
    task_id: str
    app_name: str
    directory: Path | None
    status: str = "started"
    files: list[str] = field(default_factory=list)
    process: object = None


class CodeManager:
    def __init__(self, settings, bus, persona, executor, assessor=None):
        self.settings = settings
        self.bus = bus
        self.persona = persona
        self.executor = executor
        self.assessor = assessor
        self.task = None
        self.jobs = {}
        self.fake_delay = 1.5

    @property
    def busy(self):
        return self.task is not None and not self.task.done()

    def emit(self, job, status, note, **extra):
        job.status = status
        self.bus.publish(
            job.task_id,
            "code",
            job_id=job.job_id,
            status=status,
            note=note,
            files=job.files,
            **extra,
        )

    async def start(self, call, args):
        if self.busy:
            return ToolResult(ok=False, summary=CODE_BUSY, origin="code")
        if not re.fullmatch(r"[a-z0-9-]{1,40}", args["app_name"]):
            return ToolResult(ok=False, summary="Invalid app name.", origin="code")
        target = None
        if not self.settings.fake:
            target = confined_path(self.settings.sandbox, args["app_name"])
            if target.exists():
                return ToolResult(
                    ok=False,
                    summary="That sandbox app already exists. Use a new app name.",
                    origin="code",
                )
            target.mkdir(parents=False, exist_ok=False)
        job = CodeJob(uuid4().hex, call.task_id, args["app_name"], target)
        self.jobs[job.job_id] = job
        # Keep app data bounded for a long-running demo.
        while len(self.jobs) > 20:
            self.jobs.pop(next(iter(self.jobs)))
        self.emit(job, "started", f"Building {args['app_name']} in sandbox/.")
        self.task = asyncio.create_task(self._work(job, args["spec"]))
        await self.persona.say(call.task_id, CODE_START)
        return ToolResult(
            ok=True,
            summary="Coding job started in the background; it is not finished yet.",
            origin="code",
            data={"job_id": job.job_id, "status": "started"},
        )

    async def _narrate(self, job):
        index = 0
        while True:
            await asyncio.sleep(20)
            await self.persona.say(job.task_id, CODE_PROGRESS[index % len(CODE_PROGRESS)])
            index += 1

    async def _work(self, job, spec):
        narrator = asyncio.create_task(self._narrate(job))
        try:
            if self.settings.fake:
                await asyncio.sleep(self.fake_delay / 2)
                self.emit(job, "progress", "CSS likh raha hoon. The fake app is being prepared.")
                await asyncio.sleep(self.fake_delay / 2)
                job.files = ["index.html"]
            else:
                await self._codex(job, spec)
            # Completion means an actual, nonempty entrypoint exists, not merely exit 0.
            if job.directory:
                entry = confined_path(job.directory, "index.html")
                if not entry.is_file() or entry.stat().st_size == 0:
                    raise ValueError("Codex did not produce index.html")
                job.files = [
                    str(path.relative_to(job.directory))
                    for path in sorted(job.directory.rglob("*"))
                    if path.is_file()
                    and not path.is_symlink()
                    and not any(
                        part.startswith(".") for part in path.relative_to(job.directory).parts
                    )
                ]
            await self._open(job)
            self.emit(
                job, "done", "Ho gaya. Billu's app is ready.", url=f"/apps/{job.job_id}/index.html"
            )
            self.persona.set_mood(job.task_id, "proud", "coding job finished")
            await self.persona.say(job.task_id, CODE_DONE)
        except asyncio.CancelledError:
            await self._kill(job)
            self.emit(job, "failed", "Coding job stopped with Catbot.")
            raise
        except Exception as exc:  # noqa: BLE001 - redact Codex output and provider failures
            await self._kill(job)
            self.emit(
                job, "failed", f"Coding stopped safely ({type(exc).__name__}). Try a new app name."
            )
            await self.persona.say(job.task_id, CODE_FAILED)
        finally:
            narrator.cancel()
            await asyncio.gather(narrator, return_exceptions=True)

    async def _codex(self, job, spec):
        prompt = (
            spec + "\n\nFixed rules: Build only a small plain HTML, CSS and JavaScript app. "
            "No dependencies, no installs, no network or external assets. Entry point index.html. "
            "Credit Billu as the maker, with Catbot as the product. Unless the spec specifies a look, "
            "use a Delhi tapri night palette: green-black, paper-white and muted green. "
            "No cream page, gradients, glow, offset-box shadows, crushed tracking or clipped type. "
            "Use generous padding, readable contrast, visible default content, 44px controls and "
            "visible keyboard focus. Buttons must not translate or scale on hover. "
            "All buttons must work. Finish quickly. Do not use tools outside this directory. "
            "Do not read or change the parent repository, model, .env, settings or credentials. "
            "Do not run a server or open the browser. The parent Catbot process handles opening. "
            "Do not spawn agents. Only make the requested app. Keep all files inside this directory."
        )
        binary = shutil.which("codex")
        if not binary:
            raise FileNotFoundError("Codex CLI is not installed")
        env = {
            key: value
            for key, value in os.environ.items()
            if not any(word in key.upper() for word in ("KEY", "TOKEN", "SECRET", "PASSWORD"))
        }
        # CLI authentication uses its own login. No OpenAI key is read by Catbot.
        model = os.getenv("CODEX_MODEL", "gpt-5.6-terra")
        argv = [
            binary,
            "exec",
            "-m",
            model,
            "-C",
            str(job.directory),
            "-s",
            "workspace-write",
            "--skip-git-repo-check",
            "--ephemeral",
            "--json",
            "-o",
            str(job.directory / ".codex-last.txt"),
            prompt,
        ]
        job.process = await asyncio.create_subprocess_exec(
            *argv,
            cwd=job.directory,
            env=env,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            start_new_session=True,
            limit=1024 * 1024,
        )

        async def stdout():
            while line := await job.process.stdout.readline():
                try:
                    event = json.loads(line)
                except (ValueError, UnicodeError):
                    continue
                kind = event.get("type", "")
                item = event.get("item", {})
                item_type = item.get("type", "")
                # Only fixed notes from event types; model output is never executable control text.
                if kind in {"item.started", "item.completed"}:
                    note = {
                        "file_change": "Writing app files.",
                        "command_execution": "Checking the local app.",
                        "agent_message": "Billu is working on the app.",
                    }.get(item_type)
                    if note:
                        self.emit(job, "progress", note)
                if kind in {"turn.failed", "error"}:
                    raise RuntimeError("Codex reported a failed turn")

        async def stderr():
            # Drain without logging: diagnostic streams can contain environment or request context.
            while await job.process.stderr.read(4096):
                pass

        async with asyncio.timeout(180):
            await asyncio.gather(stdout(), stderr())
            code = await job.process.wait()
        if code != 0:
            raise RuntimeError("Codex exited unsuccessfully")

    async def _kill(self, job):
        process = job.process
        if process is not None and process.returncode is None:
            if os.name != "nt":
                import signal

                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
            else:
                process.kill()
            await process.wait()

    async def _open(self, job):
        # A fresh, explicit policy decision for the fixed follow-up. Codex text cannot request it.
        call = ToolCall(
            task_id=job.task_id,
            step=1,
            call_id=uuid4().hex,
            tool="run_command",
            args={
                "command": "start index.html"
                if self.settings.os_name == "windows"
                else "open index.html"
            },
            request_en="Open the completed local app that the user asked Billu to build",
        )
        risk = await self.assessor(call) if self.assessor else decision(call)
        token = self.executor.authorize(call, risk)
        self.bus.publish(
            job.task_id,
            "risk",
            tier=risk.tier.model_dump(),
            verify=risk.verify.model_dump(),
            floor=None,
            latency_ms=0,
            follow_up=True,
        )
        self.bus.publish(job.task_id, "gate", verdict=token.verdict.model_dump(), follow_up=True)
        result = await self.executor.execute(call, token, cwd=job.directory)
        if not result.ok:
            # The app still exists; e.g. a headless machine has no default browser.
            self.emit(job, "progress", "App is ready. Open it using the link in the code panel.")

    def asset(self, job_id, relative):
        job = self.jobs.get(job_id)
        if job is None or job.status != "done":
            return None
        if self.settings.fake:
            return FAKE_APP if relative == "index.html" else None
        path = confined_path(job.directory, relative)
        if not path.is_file() or any(part.startswith(".") for part in Path(relative).parts):
            return None
        if path.suffix.lower() not in {
            ".html",
            ".css",
            ".js",
            ".json",
            ".svg",
            ".png",
            ".jpg",
            ".jpeg",
            ".webp",
            ".woff2",
        }:
            return None
        return path

    async def close(self):
        if self.busy:
            self.task.cancel()
            await asyncio.gather(self.task, return_exceptions=True)
