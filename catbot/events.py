import asyncio
import re
from collections import deque
from datetime import UTC, datetime

from catbot.contracts import Event


class EventBus:
    def __init__(self):
        self.history = deque(maxlen=100)
        self.secrets = ()
        self.subscribers: set[asyncio.Queue] = set()

    def redact(self, value):
        if isinstance(value, str):
            for secret in self.secrets:
                if len(secret) >= 6:
                    value = value.replace(secret, "[redacted]")
            return re.sub(
                r"(?i)(\b(?:otp|pin|password|api[_ -]?key|access[_ -]?token)\s*[:=]?\s+)[\w-]{3,}",
                r"\1[redacted]",
                value,
            )
        if isinstance(value, dict):
            return {
                key: (
                    "[redacted]"
                    if re.fullmatch(r"(?i)password|api[_ -]?key|token|secret", str(key))
                    else self.redact(item)
                )
                for key, item in value.items()
            }
        if isinstance(value, (list, tuple)):
            return [self.redact(item) for item in value]
        return value

    def publish(self, task_id: str, stage: str, **payload):
        event = Event(
            ts=datetime.now(UTC).isoformat(),
            task_id=task_id,
            stage=stage,
            payload=self.redact(payload),
        )
        self.history.append(event)
        for queue in tuple(self.subscribers):
            if queue.full():
                queue.get_nowait()
            queue.put_nowait(event)
        return event

    def subscribe(self):
        queue = asyncio.Queue(maxsize=200)
        self.subscribers.add(queue)
        return queue

    def unsubscribe(self, queue):
        self.subscribers.discard(queue)
