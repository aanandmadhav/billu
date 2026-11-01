import asyncio
from collections import deque
from datetime import UTC, datetime

from catbot.contracts import Event


class EventBus:
    def __init__(self):
        self.history = deque(maxlen=100)
        self.subscribers: set[asyncio.Queue] = set()

    def publish(self, task_id: str, stage: str, **payload):
        event = Event(
            ts=datetime.now(UTC).isoformat(), task_id=task_id, stage=stage, payload=payload
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
