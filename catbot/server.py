import asyncio
import base64
import io
import json
import secrets
import time
import wave
from contextlib import asynccontextmanager
from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from starlette.middleware.trustedhost import TrustedHostMiddleware

from catbot.config import ROOT
from catbot.loop import Runner
from catbot.voice import VoiceSession

UI = Path(__file__).parent / "ui"


class TextInput(BaseModel):
    utterance: str = Field(min_length=1, max_length=4000)


class ConfirmInput(BaseModel):
    task_id: str = Field(min_length=1, max_length=80)
    reply: str = Field(min_length=1, max_length=300)


class CorrectionInput(BaseModel):
    task_id: str = Field(min_length=1, max_length=80)
    decision: str
    choice: str


def same_origin(origin, host):
    return not origin or origin in {f"http://{host}", f"https://{host}"}


class AudioHub:
    def __init__(self, bus=None):
        self.bus = bus
        self.peers = set()
        self.pending = {}
        self.interrupted_at = 0
        self.last_audio = None

    async def speak(self, task_id, audio, *, started=None, text=None):
        if started is not None and started <= self.interrupted_at:
            return
        peers = tuple(self.peers)
        if not peers:
            return
        speech_id = uuid4().hex
        future = asyncio.get_running_loop().create_future()
        self.pending[speech_id] = (future, set(peers))
        self.last_audio = {
            "speech_id": speech_id,
            "provider": "sarvam" if audio else "system",
            "status": "sending",
        }
        try:
            for ws in peers:
                try:
                    await ws.send_json(
                        {
                            "type": "tts",
                            "task_id": task_id,
                            "speech_id": speech_id,
                            "audio": audio,
                            "text": text,
                        }
                    )
                except (RuntimeError, WebSocketDisconnect):
                    self.peers.discard(ws)
            try:
                with wave.open(io.BytesIO(base64.b64decode(audio or "")), "rb") as wav:
                    duration = wav.getnframes() / wav.getframerate()
            except (ValueError, EOFError, wave.Error):
                duration = max(3, len((text or "").split()) * 0.55)
            # Wait for the audible line to finish, so mute cannot cut off Billu's last words.
            return await asyncio.wait_for(future, timeout=min(40, duration + 4))
        except TimeoutError:
            if self.bus:
                self.bus.publish(
                    task_id,
                    "audio_error",
                    message="Speech playback did not finish. Check your sound output.",
                )
            return False
        finally:
            self.pending.pop(speech_id, None)

    def interrupt(self):
        self.interrupted_at = time.monotonic()
        for future, _ in self.pending.values():
            if not future.done():
                future.set_result(False)

    def acknowledge(self, ws, speech_id, status="completed", provider=None):
        pending = self.pending.get(speech_id)
        if pending and ws in pending[1] and not pending[0].done():
            pending[0].set_result(status == "completed")
            if self.last_audio and self.last_audio["speech_id"] == speech_id:
                self.last_audio["status"] = status
                if provider in {"sarvam", "system"}:
                    self.last_audio["provider"] = provider
            if self.bus:
                self.bus.publish("audio", "audio", status=status, speech_id=speech_id)


def create_app(settings, *, runner=None):
    runner = runner or Runner(settings, audio=True)
    audio = AudioHub(runner.bus)
    runner.persona.audio_sink = audio.speak
    jobs = set()
    corrections = []

    async def idle_watch():
        while True:
            await asyncio.sleep(10)
            if (
                not runner.busy
                and time.monotonic() - runner.last_activity >= 120
                and runner.persona.mood != "sleepy"
            ):
                runner.persona.set_mood("idle", "sleepy", "idle for two minutes")

    @asynccontextmanager
    async def lifespan(app):
        runner.start()
        idle = asyncio.create_task(idle_watch())
        yield
        idle.cancel()
        for job in tuple(jobs):
            job.cancel()
        await asyncio.gather(idle, *jobs, return_exceptions=True)
        await runner.close()

    app = FastAPI(title="Catbot: Billu", lifespan=lifespan)
    app.state.runner = runner
    app.state.audio = audio
    app.add_middleware(
        TrustedHostMiddleware, allowed_hosts=["127.0.0.1", "localhost", "testserver"]
    )

    def authorized(headers):
        return not settings.desktop_token or secrets.compare_digest(
            headers.get("authorization", ""), "Bearer " + settings.desktop_token
        )

    @app.middleware("http")
    async def local_origin(request: Request, call_next):
        if not authorized(request.headers):
            return JSONResponse(
                {"detail": "This backend belongs to the Catbot desktop app."}, status_code=401
            )
        if request.method != "GET" and (
            not same_origin(request.headers.get("origin"), request.headers.get("host"))
            or request.headers.get("sec-fetch-site") == "cross-site"
        ):
            return JSONResponse(
                {"detail": "Only the local Catbot page can send commands."}, status_code=403
            )
        return await call_next(request)

    fonts = UI / "fonts" if (UI / "fonts/gloock.woff2").is_file() else ROOT / "assets/fonts"
    app.mount("/ui/fonts", StaticFiles(directory=fonts), name="fonts")
    app.mount("/ui", StaticFiles(directory=UI), name="ui")

    @app.get("/")
    async def index(request: Request):
        csp = (
            "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data:; font-src 'self'; media-src 'self' blob: data:; "
            f"connect-src 'self' ws://{request.headers['host']}; "
            "object-src 'none'; frame-src 'none'; base-uri 'none'; form-action 'self'"
        )
        return FileResponse(UI / "index.html", headers={"Content-Security-Policy": csp})

    @app.get("/apps/{job_id}/{relative:path}")
    async def app_asset(job_id: str, relative: str):
        try:
            asset = runner.code.asset(job_id, relative)
        except ValueError:
            asset = None
        if asset is None:
            raise HTTPException(404, "App file not found.")
        headers = {
            "Content-Security-Policy": "sandbox allow-scripts; default-src 'none'; script-src 'unsafe-inline' 'self'; style-src 'unsafe-inline' 'self'; img-src data: 'self'; font-src 'self'; connect-src 'none'; form-action 'none'; base-uri 'none'",
            "X-Content-Type-Options": "nosniff",
            "Referrer-Policy": "no-referrer",
        }
        return (
            HTMLResponse(asset, headers=headers)
            if isinstance(asset, str)
            else FileResponse(asset, headers=headers)
        )

    @app.get("/api/stats")
    async def stats():
        return {
            "gate": "laya" if runner.laya.ready else "keyword",
            "laya_ready": runner.laya.ready,
            "os": settings.os_name,
            "fake": settings.fake,
            "mime": runner.persona.mime,
            "corrections": len(corrections),
            "sandbox": "sandbox/",
            "voice": {"connected": bool(audio.peers), "last": audio.last_audio},
        }

    @app.post("/api/voice/test")
    async def voice_test():
        if runner.persona.mime:
            raise HTTPException(409, "Billu is in mime mode. Restore volume first.")
        if not audio.peers:
            raise HTTPException(409, "Voice is not connected. Enable voice and try again.")
        task_id = "voice-test-" + uuid4().hex
        played = await runner.persona.say(
            task_id, "Billu bol raha hoon. Awaaz aa rahi hai? Chalo, ab kaam bolo."
        )
        if not played:
            raise HTTPException(
                503, "Voice did not finish playing. Check your selected sound output and try again."
            )
        return {"ok": True, "task_id": task_id, "provider": "system" if settings.fake else "sarvam"}

    @app.post("/api/text", status_code=202)
    async def text(body: TextInput):
        utterance = body.utterance.strip()
        if not utterance:
            raise HTTPException(422, "Type a command first.")
        if runner.persona.is_payment(utterance):
            return {"task_id": "tease-payment", "answer": True}
        if runner.pending:
            task_id = next(iter(runner.pending))
            runner.answer(task_id, utterance)
            return {"task_id": task_id, "answer": True}
        if runner.busy:
            raise HTTPException(409, "Billu is finishing the current request.")
        task_id = await runner.submit_transcript(utterance)
        return {"task_id": task_id}

    @app.post("/api/confirm")
    async def confirm(body: ConfirmInput):
        if not runner.answer(body.task_id, body.reply):
            raise HTTPException(409, "That confirmation is no longer waiting.")
        return {"ok": True}

    @app.post("/api/pet")
    async def pet():
        paid = getattr(runner.persona, "pay", lambda *_: False)("pet")
        runner.bus.publish("pet", "pet", sound="purr", paid=paid)
        return {"ok": True, "paid": paid}

    @app.post("/api/treat")
    async def treat():
        paid = getattr(runner.persona, "pay", lambda *_: False)("treat")
        runner.bus.publish("treat", "treat", sound="slurp", paid=paid)
        return {"ok": True, "paid": paid}

    @app.post("/api/correction")
    async def correction(body: CorrectionInput):
        choices = {
            "tier": {"T0", "T1", "T2", "T3"},
            "verify": {"execute", "wrong_tool", "unclear"},
            "reply": {"A", "B", "C"},
        }
        if body.decision not in choices or body.choice not in choices[body.decision]:
            raise HTTPException(422, "Choose one of the decision's valid labels.")
        if not any(e.task_id == body.task_id for e in runner.bus.history):
            raise HTTPException(404, "Task not found in this session.")
        corrections.append(body.model_dump())
        runner.bus.publish(
            body.task_id,
            "correction",
            **body.model_dump(exclude={"task_id"}),
            count=len(corrections),
        )
        return {"ok": True, "count": len(corrections)}

    @app.websocket("/events")
    async def events(ws: WebSocket):
        if not authorized(ws.headers) or not same_origin(
            ws.headers.get("origin"), ws.headers.get("host")
        ):
            await ws.close(code=1008)
            return
        await ws.accept()
        queue = runner.bus.subscribe()
        try:
            for event in list(runner.bus.history)[-50:]:
                await ws.send_json(event.model_dump())
            while True:
                event = await queue.get()
                await ws.send_json(event.model_dump())
        except (WebSocketDisconnect, RuntimeError):
            pass
        finally:
            runner.bus.unsubscribe(queue)

    @app.websocket("/audio")
    async def audio_socket(ws: WebSocket):
        if not authorized(ws.headers) or not same_origin(
            ws.headers.get("origin"), ws.headers.get("host")
        ):
            await ws.close(code=1008)
            return
        await ws.accept()
        session = None
        try:
            while True:
                packet = await ws.receive()
                if packet["type"] == "websocket.disconnect":
                    break
                frame = packet.get("bytes")
                if frame is not None:
                    if session:
                        try:
                            await session.feed(frame)
                        except ValueError as exc:
                            await ws.send_json({"type": "error", "message": str(exc)})
                            await session.cancel()
                            session = None
                    continue
                try:
                    message = json.loads(packet.get("text") or "{}")
                except ValueError:
                    await ws.send_json(
                        {"type": "error", "message": "Invalid audio control message."}
                    )
                    continue
                if not isinstance(message, dict):
                    await ws.send_json(
                        {"type": "error", "message": "Audio control must be a JSON object."}
                    )
                    continue
                kind = message.get("type")
                if kind == "played":
                    audio.acknowledge(
                        ws,
                        message.get("speech_id"),
                        message.get("status", "completed"),
                        message.get("provider"),
                    )
                elif kind == "playback":
                    if message.get("enabled") is True:
                        audio.peers.add(ws)
                    else:
                        audio.peers.discard(ws)
                elif kind == "interrupt":
                    audio.interrupt()
                elif kind == "start":
                    if session:
                        await session.cancel()
                    audio.interrupt()
                    session = VoiceSession(runner, ws.send_json)
                    session.start()
                    await ws.send_json({"type": "recording", "fake": settings.fake})
                elif kind == "stop" and session:
                    try:
                        await session.finish()
                    except TimeoutError:
                        await session.cancel()
                        await ws.send_json(
                            {"type": "error", "message": "Voice connection timed out."}
                        )
                    session = None
        except (WebSocketDisconnect, RuntimeError, ValueError):
            pass
        finally:
            if session:
                await session.cancel()
            audio.peers.discard(ws)

    return app
