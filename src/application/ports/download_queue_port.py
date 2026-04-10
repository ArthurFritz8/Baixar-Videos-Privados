from abc import ABC, abstractmethod


class DownloadQueuePort(ABC):
    @abstractmethod
    async def enqueue(self, download_id: str) -> None:
        raise NotImplementedError

    @abstractmethod
    async def dequeue(self) -> str | None:
        raise NotImplementedError

    @abstractmethod
    def task_done(self) -> None:
        raise NotImplementedError

    @abstractmethod
    async def close(self) -> None:
        raise NotImplementedError
