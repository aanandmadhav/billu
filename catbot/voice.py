"""Push-to-talk sessions. Audio stays in memory; empty captures never reach STT."""

import asyncio
import base64
import math
import re
import struct
from collections import deque
from uuid import uuid4


class VoiceInputError(Exception):
    def __init__(self, code, message, *, provider_code=None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.provider_code = provider_code


def provider_error(code):
    """Classify provider codes without reflecting provider payloads or credentials."""
    value = str(code or "provider_error").lower()
    safe_code = value if re.fullmatch(r"[a-z0-9_-]{1,60}", value) else "provider_error"
    if any(word in value for word in ("auth", "key", "forbidden", "unauthor", "401", "403")):
        return VoiceInputError(
            "authentication",
            "Sarvam rejected voice access. Check SARVAM_API_KEY in .env and restart Catbot.",
            provider_code=safe_code,
        )
    if any(word in value for word in ("quota", "rate", "concurr", "limit", "429")):
        return VoiceInputError(
            "rate_limit",
            "Sarvam voice is busy or out of quota. Wait a moment and retry; check your Sarvam quota if it continues.",
            provider_code=safe_code,
        )
    if value == "transcriber_error":
        return VoiceInputError(
            "transcription_failed",
            "That recording could not be transcribed. Hold Space while speaking, then release and try again.",
            provider_code=safe_code,
        )
    return VoiceInputError(
        "provider_error",
        "The speech service could not process the recording. Release the talk button and try again.",
        provider_code=safe_code,
    )


class VoiceSession:
    def __init__(self, runner, notify):
        self.runner = runner
        self.notify = notify
        self.task_id = runner.active_task or uuid4().hex
        self.frames = asyncio.Queue(maxsize=64)
        self.task = None
        self.closed = False
        self.received = 0
        self.peak = 0
        self.reported = False

    def start(self):
        self.runner.bus.publish(self.task_id, "listen", partial="", lang="hi-IN", level=0)
        self.task = asyncio.create_task(self._run())

    async def feed(self, frame):
        if self.closed or (self.task and self.task.done()):
            return
        if len(frame) != 3200:
            raise ValueError("Audio frames must be exactly 3,200 bytes.")
        self.received += len(frame)
        if self.received > 32000 * 30:
            raise ValueError("Hold-to-talk is limited to 30 seconds.")
        samples = struct.unpack("<1600h", frame)
        self.peak = max(self.peak, max(abs(sample) for sample in samples))
        level = min(1, math.sqrt(sum(s * s for s in samples) / 1600) / 12000)
        self.runner.bus.publish(self.task_id, "listen", level=level, lang="hi-IN")
        try:
            self.frames.put_nowait(frame)
        except asyncio.QueueFull:
            raise ValueError("Voice connection is too slow. Release and try again.") from None

    async def finish(self):
        if self.closed:
            return
        self.closed = True
        if self.task and self.task.done():
            await self.task
            return
        try:
            await asyncio.wait_for(self.frames.put(None), timeout=2)
            if self.task:
                await asyncio.wait_for(self.task, timeout=12)
        except TimeoutError:
            await self.cancel()
            await self.report(
                VoiceInputError(
                    "timeout",
                    "Speech recognition timed out. Release the talk button and try again.",
                )
            )

    async def cancel(self):
        self.closed = True
        if self.task:
            if not self.task.done():
                self.task.cancel()
            await asyncio.gather(self.task, return_exceptions=True)

    async def report(self, error):
        if self.reported:
            return
        self.reported = True
        diagnostic = {
            "code": error.code,
            "provider_code": error.provider_code,
            "audio_ms": self.received // 32,
            "peak": self.peak,
        }
        self.runner.bus.publish(
            self.task_id, "error", scope="voice_input", message=error.message, **diagnostic
        )
        await self.notify(
            self.runner.bus.redact(
                {"type": "error", "message": error.message, "stop_recording": True, **diagnostic}
            )
        )
        if self.task_id != self.runner.active_task:
            self.runner.bus.publish(self.task_id, "done", ok=False, stopped_by=error.code)

    async def _run(self):
        try:
            if self.runner.settings.fake:
                while await self.frames.get() is not None:
                    pass
                reply = (
                    "haan"
                    if self.runner.pending
                    else "chai"
                    if self.runner.persona.payment is not None
                    else "volume kam karo"
                )
                await self.runner.submit_transcript(reply, task_id=self.task_id, lang="hi-IN")
                return
            await self._real()
        except asyncio.CancelledError:
            raise
        except VoiceInputError as exc:
            await self.report(exc)
        except TimeoutError:
            await self.report(
                VoiceInputError(
                    "timeout",
                    "The voice connection timed out. Check your connection and try again.",
                )
            )
        except Exception as exc:  # noqa: BLE001 - redact SDK/network diagnostics at the voice boundary
            status = getattr(exc, "status_code", None)
            code = getattr(exc, "code", None)
            if status in {401, 403}:
                error = provider_error(str(status))
            elif status == 429 or code == 1003:
                error = VoiceInputError(
                    "access_or_quota",
                    "Sarvam closed voice access. Check your API key and voice quota, then retry.",
                )
            elif code == 4000:
                error = VoiceInputError(
                    "configuration",
                    "Sarvam rejected the speech configuration. Restart Catbot and retry.",
                )
            else:
                error = VoiceInputError(
                    "connection",
                    "The speech connection was interrupted. Check your connection and try again.",
                )
            await self.report(error)

    async def _initial_audio(self):
        # Keep a short pre-roll, but do not open a paid streaming session for an empty
        # press or a microphone delivering only digital silence. Quiet speech is retained.
        preroll = deque(maxlen=2)
        while (frame := await self.frames.get()) is not None:
            samples = struct.unpack("<1600h", frame)
            if any(samples):
                return [*preroll, frame]
            preroll.append(frame)
        if not self.received:
            raise VoiceInputError(
                "no_audio", "No audio was recorded. Hold Space while speaking, then release."
            )
        raise VoiceInputError(
            "silent_input",
            "Your microphone sent only silence. Check the selected microphone in system sound settings, then try again.",
        )

    async def _real(self):
        from sarvamai import (
            AsyncSarvamAI,
            RealtimeAudioInput,
            RealtimeEnd,
            RealtimeSpeechEnd,
            RealtimeSpeechStart,
        )

        initial = await self._initial_audio()
        client = AsyncSarvamAI(api_subscription_key=self.runner.settings.sarvam_key)
        async with client.speech_to_text_realtime_streaming.connect(
            language_code="auto",
            model="saaras:v3-realtime",
            stream_type="fast",
            endpointing="manual",
            encoding="linear16",
            sample_rate="16000",
        ) as socket:
            await socket.send_realtime_speech_start(RealtimeSpeechStart())

            async def send():
                for frame in initial:
                    await socket.send_realtime_audio_input(
                        RealtimeAudioInput(audio=base64.b64encode(frame).decode())
                    )
                while (frame := await self.frames.get()) is not None:
                    await socket.send_realtime_audio_input(
                        RealtimeAudioInput(audio=base64.b64encode(frame).decode())
                    )
                await socket.send_realtime_speech_end(RealtimeSpeechEnd())

            async def receive():
                async for event in socket:
                    data = (
                        event.model_dump(exclude_none=True)
                        if hasattr(event, "model_dump")
                        else event
                    )
                    if not isinstance(data, dict):
                        continue
                    kind = data.get("event")
                    if kind == "transcript.partial":
                        self.runner.bus.publish(
                            self.task_id,
                            "listen",
                            partial=data.get("text", ""),
                            lang=data.get("language", "hi-IN"),
                        )
                    elif kind == "transcript.final":
                        text = data.get("text", "").strip()
                        language = (
                            data.get("language", "hi-IN")
                            if data.get("language_confidence", 0) >= 0.8
                            else "hi-IN"
                        )
                        if not text:
                            raise VoiceInputError(
                                "no_speech",
                                "No speech was recognized. Hold Space while speaking, then release and try again.",
                            )
                        await self.runner.submit_transcript(
                            text, task_id=self.task_id, lang=language
                        )
                        return
                    elif kind == "error":
                        raise provider_error(data.get("code"))
                    elif kind == "session.end":
                        raise VoiceInputError(
                            "no_transcript",
                            "The speech service ended before recognizing your recording. Hold Space while speaking, then try again.",
                        )
                raise VoiceInputError(
                    "connection",
                    "The speech connection closed before recognizing your recording. Try again.",
                )

            sender = asyncio.create_task(send())
            receiver = asyncio.create_task(receive())
            try:
                async with asyncio.timeout(45):
                    await asyncio.gather(sender, receiver)
                await socket.send_realtime_end(RealtimeEnd())
            finally:
                sender.cancel()
                receiver.cancel()
                await asyncio.gather(sender, receiver, return_exceptions=True)
