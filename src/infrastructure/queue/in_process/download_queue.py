import asyncio

from src.application.ports.download_queue_port import DownloadQueuePort


class InProcessDownloadQueue(DownloadQueuePort):
    def __init__(self) -> None:
        self._queue: asyncio.Queue[str] = asyncio.Queue()

    async def enqueue(self, download_id: str) -> None:
        await self._queue.put(download_id)

    async def dequeue(self) -> str | None:
        return await self._queue.get()

    def task_done(self) -> None:
        self._queue.task_done()

    async def close(self) -> None:
        return
