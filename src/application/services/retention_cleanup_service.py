from datetime import UTC, datetime, timedelta
from pathlib import Path

from src.application.ports.download_job_repository_port import DownloadJobRepositoryPort
from src.infrastructure.observability.logger import get_logger

logger = get_logger(__name__)


class RetentionCleanupService:
    def __init__(
        self,
        download_job_repository: DownloadJobRepositoryPort,
        terminal_job_retention_hours: int,
    ) -> None:
        self._download_job_repository = download_job_repository
        self._terminal_job_retention_hours = terminal_job_retention_hours

    async def run_once(self) -> None:
        older_than = datetime.now(UTC) - timedelta(hours=self._terminal_job_retention_hours)
        artifact_locations = self._download_job_repository.prune_terminal_jobs(older_than)

        removed_artifacts = 0
        for location in artifact_locations:
            try:
                candidate = Path(location)
                if candidate.exists() and candidate.is_file():
                    candidate.unlink()
                    removed_artifacts += 1
            except OSError as exc:
                logger.warning("cleanup_artifact_remove_error path=%s detail=%s", location, exc)

        logger.info(
            "cleanup_completed removed_jobs=%s removed_artifacts=%s",
            len(artifact_locations),
            removed_artifacts,
        )
