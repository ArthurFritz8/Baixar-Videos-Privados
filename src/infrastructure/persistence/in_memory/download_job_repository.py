from dataclasses import replace
from threading import RLock

from src.domain.entities.download_job import DownloadJob


class InMemoryDownloadJobRepository:
    def __init__(self) -> None:
        self._jobs: dict[str, DownloadJob] = {}
        self._lock = RLock()

    def create_if_absent(self, job: DownloadJob) -> tuple[DownloadJob, bool]:
        with self._lock:
            existing = self._jobs.get(job.download_id)
            if existing is not None:
                return replace(existing), False

            self._jobs[job.download_id] = job
            return replace(job), True

    def get(self, download_id: str) -> DownloadJob | None:
        with self._lock:
            job = self._jobs.get(download_id)
            return replace(job) if job is not None else None

    def mark_processing(self, download_id: str) -> DownloadJob | None:
        with self._lock:
            job = self._jobs.get(download_id)
            if job is None:
                return None

            if job.queue_status in ("completed", "failed", "canceled"):
                return replace(job)

            updated = job.to_processing()
            self._jobs[download_id] = updated
            return replace(updated)

    def mark_completed(
        self,
        download_id: str,
        artifact_location: str | None,
        attempt_count: int,
    ) -> DownloadJob | None:
        with self._lock:
            job = self._jobs.get(download_id)
            if job is None:
                return None

            updated = job.to_completed(
                artifact_location=artifact_location,
                attempt_count=attempt_count,
            )
            self._jobs[download_id] = updated
            return replace(updated)

    def mark_failed(
        self,
        download_id: str,
        error_code: str,
        attempt_count: int,
    ) -> DownloadJob | None:
        with self._lock:
            job = self._jobs.get(download_id)
            if job is None:
                return None

            updated = job.to_failed(error_code=error_code, attempt_count=attempt_count)
            self._jobs[download_id] = updated
            return replace(updated)

    def mark_canceled(self, download_id: str, error_code: str) -> DownloadJob | None:
        with self._lock:
            job = self._jobs.get(download_id)
            if job is None:
                return None

            if job.queue_status in ("completed", "failed", "canceled", "processing"):
                return replace(job)

            updated = job.to_canceled(error_code=error_code)
            self._jobs[download_id] = updated
            return replace(updated)
