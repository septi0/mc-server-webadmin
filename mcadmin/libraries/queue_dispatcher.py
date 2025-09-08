import asyncio
import logging

__all__ = ["QueueDispatcher"]

logger = logging.getLogger(__name__)

class EventQueue(asyncio.Queue):

    def __init__(self, event_type: str, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.event_type = event_type


class QueueDispatcher:
    def __init__(self, q: asyncio.Queue, buffer_size: int = 20, subs_queue_max_size: int = 100):
        self._queue: asyncio.Queue = q
        self._subs: set[EventQueue] = set()
        self._buffer_size: int = buffer_size
        self._subs_queue_max_size: int = subs_queue_max_size

        self._fanout_task: asyncio.Task | None = None
        self._buffer: dict = {}

        if self._buffer_size > self._subs_queue_max_size:
            raise ValueError(f"Buffer size cannot be greater than subscriber queue max size ({self._subs_queue_max_size})")

    def subscribe(self, event_type: str, *, scrollback: int = 0) -> EventQueue:
        q = EventQueue(event_type, maxsize=self._subs_queue_max_size)

        self._subs.add(q)

        if scrollback > self._buffer_size:
            raise ValueError(f"Scrollback cannot be greater than buffer size ({self._buffer_size})")

        for item in self._buffer.get(event_type, [])[-scrollback:]:
            q.put_nowait(item)

        logger.debug(f"New subscriber added. Total subscribers: {len(self._subs)}")

        return q

    def unsubscribe(self, q: EventQueue):
        if not q in self._subs:
            logger.warning("Attempted to unsubscribe a non-subscriber")
            return

        self._subs.remove(q)
        logger.debug(f"Subscriber removed. Total subscribers: {len(self._subs)}")

    async def start(self) -> None:
        if self._fanout_task and not self._fanout_task.done():
            return

        logger.info("Starting queue dispatcher")

        self._fanout_task = asyncio.create_task(self._fanout())

    async def stop(self) -> None:
        if not self._fanout_task or self._fanout_task.done():
            return

        logger.info("Stopping queue dispatcher")

        self._fanout_task.cancel()
        asyncio.gather(self._fanout_task, return_exceptions=True)
        self._fanout_task = None

        self._subs.clear()

    async def _fanout(self) -> None:
        while True:
            (event_type, item) = await self._queue.get()

            for sub in self._subs:
                if sub.event_type and sub.event_type != event_type:
                    continue

                try:
                    sub.put_nowait(item)
                except asyncio.QueueFull:
                    # drop oldest then retry once
                    sub.get_nowait()
                    sub.task_done()
                    sub.put_nowait(item)

            self._queue.task_done()

            event_buffer = self._buffer.get(event_type, [])
            event_buffer.append(item)

            if len(event_buffer) > self._buffer_size:
                event_buffer.pop(0)

            self._buffer[event_type] = event_buffer
