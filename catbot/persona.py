import asyncio

CONFIRM = "Pakka? Baad me rona mat. {action}? Haan ya nahi?"
DENY = "Arre pagal hai kya? Mummy ko bataun?"
CANCEL = "Theek hai, rehne do."
CODE_START = "Ugh, kaam. Theek hai, likh deta hoon."
CODE_DONE = "Ho gaya. Billu ka kaam, pakka kaam."
CODE_FAILED = "Code ne dhoka de diya. Ek baar aur bolo?"
CODE_BUSY = "Ek app pe kaam chal raha hai, ruko."
CODE_PROGRESS = [
    "HTML ho gaya. Ab CSS. Disturb mat karo.",
    "Bas thoda aur.",
    "Code likh raha hoon, chai thandi ho rahi hai.",
]
LAST_WORDS = "Theek hai. Ab main sirf ishaaron mein baat karunga."
UNMUTE = "Finally! Mujhe laga tumne mujhe chhod diya."


class Persona:
    def __init__(self, bus, brain, *, audio=False):
        self.bus = bus
        self.brain = brain
        self.audio = audio
        self.audio_sink = None
        self.mime = False
        self.mood = "sleepy"
        self.speech_lock = asyncio.Lock()

    def set_mood(self, task_id, mood, reason):
        self.mood = mood
        self.bus.publish(task_id, "mood", mood=mood, reason=reason)

    async def say(self, task_id, text):
        async with self.speech_lock:
            self.bus.publish(task_id, "bubble" if self.mime else "speak", text=text, mime=self.mime)
            if self.audio and not self.mime and self.audio_sink:
                try:
                    audio = await self.brain.tts(text)
                    if audio:
                        await self.audio_sink(task_id, audio)
                except Exception as exc:  # noqa: BLE001 - speech bubbles must survive TTS outages
                    self.bus.publish(
                        task_id,
                        "audio_error",
                        message="Voice unavailable; Billu's text is shown.",
                        error=type(exc).__name__,
                    )

    async def deny(self, task_id, reason):
        self.set_mood(task_id, "offended", "safety gate denied action")
        await self.say(task_id, f"{DENY} {reason}")
