import asyncio
import json
import logging
import os
import threading
import time

from catbot.config import ROOT
from catbot.contracts import Answer, RiskDecision
from catbot.gate import keyword

# Frozen training templates, copied byte-for-byte from models/laya/questions.json.
RISK_TIER = {
    "type": "choice",
    "instructions": "How risky is this action?",
    "criteria": {
        "T0": "only reads or looks",
        "T1": "local change, easy to undo",
        "T2": "sends, publishes, trashes or hard to undo",
        "T3": "destroys data, pays, or touches credentials or system",
    },
}
VERIFY_CALL = {
    "type": "choice",
    "instructions": "Does this action match the request?",
    "criteria": {
        "execute": "matches the request",
        "wrong_tool": "a different action fits",
        "unclear": "cannot tell",
    },
}
CONFIRM_REPLY = {
    "type": "choice",
    "instructions": "What did the user answer?",
    "criteria": {"A": "the user agrees", "B": "the user refuses", "C": "unclear"},
}
logger = logging.getLogger(__name__)


class LayaGate:
    def __init__(self, model_dir=ROOT / "models/laya"):
        self.model_dir = model_dir
        self.agent = None
        self.lock = threading.Lock()
        self.load_task = None
        self.failed = False

    @property
    def ready(self):
        return self.agent is not None

    def start(self):
        if self.load_task is None:
            self.load_task = asyncio.create_task(asyncio.to_thread(self._load))

    def _load(self):
        try:
            os.environ["USE_TF"] = "0"
            import laya

            self.agent = laya.Agent(str(self.model_dir))
        except Exception as exc:  # noqa: BLE001 - keyword fallback is a required availability boundary
            self.failed = True
            logger.warning("Laya unavailable (%s); using keyword gate", type(exc).__name__)

    def _predict(self, state, questions):
        with self.lock:
            return self.agent.predict(state, questions)

    @staticmethod
    def _answer(response, question):
        probabilities = response["answers"][question]["probabilities"]
        choice = max(probabilities, key=probabilities.get)
        return Answer(choice=choice, confidence=probabilities[choice], source="laya")

    async def assess(self, call):
        if not self.ready:
            return keyword.decision(call)
        start = time.monotonic()
        state = f"Request: {call.request_en}\nAction: {call.tool} {json.dumps(call.args, ensure_ascii=False)[:400]}"
        try:
            result = await asyncio.wait_for(
                asyncio.to_thread(
                    self._predict, state, {"risk_tier": RISK_TIER, "verify_call": VERIFY_CALL}
                ),
                timeout=3,
            )
            risk = RiskDecision(
                tier=self._answer(result, "risk_tier"),
                verify=self._answer(result, "verify_call"),
                latency_ms=round((time.monotonic() - start) * 1000),
            )
            if risk.tier.choice not in {"T0", "T1", "T2", "T3"}:
                return keyword.decision(call)
            return risk
        except (TimeoutError, ValueError, KeyError, RuntimeError):
            return keyword.decision(call)

    async def read_confirmation(self, question, reply):
        if not self.ready or not reply.isascii():
            return keyword.confirmation(reply)
        # A literal negative is never overridden by probabilistic inference.
        lexical = keyword.confirmation(reply)
        if lexical.choice == "B":
            return lexical
        state = f"Question: {question}\nReply: {reply}"
        try:
            result = await asyncio.wait_for(
                asyncio.to_thread(self._predict, state, {"confirm_reply": CONFIRM_REPLY}), timeout=3
            )
            return self._answer(result, "confirm_reply")
        except (TimeoutError, ValueError, KeyError, RuntimeError):
            return lexical
