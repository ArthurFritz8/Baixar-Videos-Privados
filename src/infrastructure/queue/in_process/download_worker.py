import asyncio

from src.application.use_cases.process_download_job_use_case import ProcessDownloadJobUseCase
from src.infrastructure.observability.logger import get_logger
from src.infrastructure.queue.in_process.download_queue import InProcessDownloadQueue

logger = get_logger(__name__)


class InProcessDownloadWorker:
    def __init__(
        self,
        download_queue: InProcessDownloadQueue,
        process_download_job_use_case: ProcessDownloadJobUseCase,
        worker_concurrency: int,
    ) -> None:
        self._download_queue = download_queue
        self._process_download_job_use_case = process_download_job_use_case
        self._worker_concurrency = max(1, worker_concurrency)
        self._tasks: list[asyncio.Task[None]] = []

    async def start(self) -> None:
        if self._tasks:
            return
        self._tasks = [
            asyncio.create_task(self._run_forever(index + 1))
            for index in range(self._worker_concurrency)
        ]
        logger.info("download_worker_started concurrency=%s", self._worker_concurrency)

    async def stop(self) -> None:
        if not self._tasks:
            return
        for task in self._tasks:
            task.cancel()
        await asyncio.gather(*self._tasks, return_exceptions=True)
        self._tasks = []
        logger.info("download_worker_stopped")

    async def _run_forever(self, worker_id: int) -> None:
        while True:
            download_id = ""
            try:
                download_id = await self._download_queue.dequeue()
                await self._process_download_job_use_case.execute(download_id)
            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.exception(
                    "download_worker_error worker_id=%s download_id=%s",
                    worker_id,
                    download_id,
                    exc_info=exc,
                )
            finally:
                if download_id:
                    self._download_queue.task_done()
