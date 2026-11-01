"""Push-to-talk sessions. No audio is stored on disk."""

import asyncio
import base64
import math
import struct
from uuid import uuid4


class VoiceSession:
    def __init__(self, runner, notify):
        self.runner = runner
        self.notify = notify
        self.task_id = runner.active_task or uuid4().hex
        self.frames = asyncio.Queue(maxsize=64)
        self.task = None
        self.closed = False
        self.received = 0

    def start(self):
        self.runner.bus.publish(self.task_id, "listen", partial="", lang="hi-IN", level=0)
        self.task = asyncio.create_task(self._run())

    async def feed(self, frame):
        if self.closed:
            return
        if len(frame) != 3200:
            raise ValueError("Audio frames must be exactly 3,200 bytes.")
        self.received += len(frame)
        if self.received > 32000 * 30:
            raise ValueError("Hold-to-talk is limited to 30 seconds.")
        samples = struct.unpack("<1600h", frame)
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
        await asyncio.wait_for(self.frames.put(None), timeout=2)
        if self.task:
            try:
                await asyncio.wait_for(self.task, timeout=12)
            except TimeoutError:
                await self.notify(
                    {"type": "error", "message": "Speech recognition timed out. Type your command."}
                )

    async def cancel(self):
        self.closed = True
        if self.task and not self.task.done():
            self.task.cancel()
            await asyncio.gather(self.task, return_exceptions=True)

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
        except Exception as exc:  # noqa: BLE001 - do not send provider diagnostics or keys to browsers
            await self.notify(
                {
                    "type": "error",
                    "message": f"Voice unavailable ({type(exc).__name__}). Type your command.",
                }
            )

    async def _real(self):
        from sarvamai import (
            AsyncSarvamAI,
            RealtimeAudioInput,
            RealtimeEnd,
            RealtimeSpeechEnd,
            RealtimeSpeechStart,
        )

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
                        if text:
                            await self.runner.submit_transcript(
                                text, task_id=self.task_id, lang=language
                            )
                        else:
                            await self.notify(
                                {
                                    "type": "error",
                                    "message": "No speech heard. Hold Space and try again.",
                                }
                            )
                        return
                    elif kind in {"error", "session.end"}:
                        raise RuntimeError("Speech session ended without a final transcript")

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
