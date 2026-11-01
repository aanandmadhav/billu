import asyncio
import re
import time

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
        self.teased = False
        self.payment = None
        self.mood = "sleepy"
        self.speech_lock = asyncio.Lock()

    def set_mood(self, task_id, mood, reason):
        self.mood = mood
        self.bus.publish(task_id, "mood", mood=mood, reason=reason)

    async def say(self, task_id, text):
        async with self.speech_lock:
            started = time.monotonic()
            self.bus.publish(task_id, "bubble" if self.mime else "speak", text=text, mime=self.mime)
            if self.audio and not self.mime and self.audio_sink:
                try:
                    audio = await self.brain.tts(text)
                    if audio:
                        await self.audio_sink(task_id, audio, started=started)
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

    def pay(self, kind="treat"):
        if self.payment is not None and not self.payment.done():
            self.payment.set_result(kind)
            return True
        return False

    def is_payment(self, text):
        if re.search(r"chai|parle|biscuit|चाय|बिस्कुट", text, re.IGNORECASE):
            return self.pay("treat")
        return False

    async def tease(self, task_id, utterance, *, enabled=True, reader=None, timeout=20):
        if (
            not enabled
            or self.teased
            or not re.search(
                r"\bvolume\s*(?:0|zero|shunya|band)\b|\bmute\b|\bawaaz band\b|आवाज़ बंद",
                utterance,
                re.IGNORECASE,
            )
        ):
            return True
        self.teased = True
        self.payment = asyncio.get_running_loop().create_future()
        self.set_mood(task_id, "chai_craving", "Billu wants chai before going quiet")
        try:
            await self.say(
                task_id,
                "Volume zero? Matlab ab sirf tum bologe, aur main chup-chaap sunta rahunga? Ek-tarfa pyaar nahi chalega, bhai. Pehle ek cutting chai pilao.",
            )
            self.bus.publish(task_id, "tease", waiting=True, expires_in=timeout)
            async with asyncio.timeout(timeout):
                if reader:
                    reply = await reader()
                    self.is_payment(reply)
                kind = await self.payment
            self.bus.publish(
                task_id,
                "pet" if kind == "pet" else "treat",
                sound="purr" if kind == "pet" else "slurp",
                paid=True,
            )
            await self.say(task_id, "Haan theek hai.")
            return True
        except TimeoutError:
            await self.say(task_id, "Theek hai, mat pilao. Volume wahi rahega.")
            return False
        finally:
            self.payment = None
            self.bus.publish(task_id, "tease", waiting=False)
