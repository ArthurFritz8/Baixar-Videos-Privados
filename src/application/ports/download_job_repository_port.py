from abc import ABC, abstractmethod
from datetime import datetime

from src.domain.entities.download_job import DownloadJob


class DownloadJobRepositoryPort(ABC):
    @abstractmethod
    def create_if_absent(self, job: DownloadJob) -> tuple[DownloadJob, bool]:
        raise NotImplementedError

    @abstractmethod
    def get(self, download_id: str) -> DownloadJob | None:
        raise NotImplementedError

    @abstractmethod
    def mark_processing(self, download_id: str) -> DownloadJob | None:
        raise NotImplementedError

    @abstractmethod
    def mark_completed(
        self,
        download_id: str,
        artifact_location: str | None,
        attempt_count: int,
    ) -> DownloadJob | None:
        raise NotImplementedError

    @abstractmethod
    def mark_failed(
        self,
        download_id: str,
        error_code: str,
        attempt_count: int,
        error_detail: str | None = None,
    ) -> DownloadJob | None:
        raise NotImplementedError

    @abstractmethod
    def mark_canceled(self, download_id: str, error_code: str) -> DownloadJob | None:
        raise NotImplementedError

    @abstractmethod
    def prune_terminal_jobs(self, older_than: datetime) -> list[str]:
        raise NotImplementedError

    @abstractmethod
    def count_by_status(self) -> dict[str, int]:
        raise NotImplementedError

    @abstractmethod
    def ping(self) -> bool:
        raise NotImplementedError
