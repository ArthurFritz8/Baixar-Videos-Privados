from dataclasses import replace
from datetime import datetime
from threading import RLock

from src.application.ports.download_job_repository_port import DownloadJobRepositoryPort
from src.domain.entities.download_job import DownloadJob


class InMemoryDownloadJobRepository(DownloadJobRepositoryPort):
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

            if job.queue_status in ("completed", "failed", "canceled"):
                return replace(job)

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
        error_detail: str | None = None,
    ) -> DownloadJob | None:
        with self._lock:
            job = self._jobs.get(download_id)
            if job is None:
                return None

            if job.queue_status in ("completed", "failed", "canceled"):
                return replace(job)

            updated = job.to_failed(
                error_code=error_code,
                attempt_count=attempt_count,
                error_detail=error_detail,
            )
            self._jobs[download_id] = updated
            return replace(updated)

    def mark_canceled(self, download_id: str, error_code: str) -> DownloadJob | None:
        with self._lock:
            job = self._jobs.get(download_id)
            if job is None:
                return None

            if job.queue_status in ("completed", "failed", "canceled"):
                return replace(job)

            updated = job.to_canceled(error_code=error_code)
            self._jobs[download_id] = updated
            return replace(updated)

    def prune_terminal_jobs(self, older_than: datetime) -> list[str]:
        removable_ids: list[str] = []
        removable_artifacts: list[str] = []
        with self._lock:
            for download_id, job in self._jobs.items():
                if (
                    job.queue_status in ("completed", "failed", "canceled")
                    and job.updated_at < older_than
                ):
                    removable_ids.append(download_id)
                    if job.artifact_location:
                        removable_artifacts.append(job.artifact_location)

            for download_id in removable_ids:
                self._jobs.pop(download_id, None)

        return removable_artifacts

    def count_by_status(self) -> dict[str, int]:
        counters = {
            "queued": 0,
            "processing": 0,
            "completed": 0,
            "failed": 0,
            "canceled": 0,
        }
        with self._lock:
            for job in self._jobs.values():
                counters[job.queue_status] = counters.get(job.queue_status, 0) + 1
        return counters

    def ping(self) -> bool:
        return True
