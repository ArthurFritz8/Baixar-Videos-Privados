from src.application.ports.download_queue_port import DownloadQueuePort


class RedisDownloadQueue(DownloadQueuePort):
    def __init__(self, redis_url: str, queue_key: str) -> None:
        try:
            from redis import asyncio as redis_async
        except Exception as exc:  # pragma: no cover - depends on optional dependency
            raise RuntimeError("redis_dependency_missing") from exc

        self._client = redis_async.from_url(redis_url, decode_responses=True)
        self._queue_key = queue_key

    async def enqueue(self, download_id: str) -> None:
        await self._client.rpush(self._queue_key, download_id)

    async def dequeue(self) -> str | None:
        item = await self._client.blpop(self._queue_key, timeout=1)
        if item is None:
            return None
        _, download_id = item
        return str(download_id)

    def task_done(self) -> None:
        return

    async def close(self) -> None:
        aclose = getattr(self._client, "aclose", None)
        if callable(aclose):
            await aclose()
            return

        close = getattr(self._client, "close", None)
        if callable(close):
            maybe_awaitable = close()
            if hasattr(maybe_awaitable, "__await__"):
                await maybe_awaitable
