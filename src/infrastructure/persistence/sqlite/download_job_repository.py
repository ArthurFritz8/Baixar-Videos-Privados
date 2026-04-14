from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from threading import RLock

from src.application.ports.download_job_repository_port import DownloadJobRepositoryPort
from src.domain.entities.download_job import DownloadJob


class SQLiteDownloadJobRepository(DownloadJobRepositoryPort):
    def __init__(self, db_path: str) -> None:
        self._db_path = Path(db_path)
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = RLock()
        self._connection = sqlite3.connect(
            self._db_path,
            check_same_thread=False,
        )
        self._connection.row_factory = sqlite3.Row
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        with self._lock:
            self._connection.execute(
                """
                CREATE TABLE IF NOT EXISTS download_jobs (
                    download_id TEXT PRIMARY KEY,
                    provider TEXT NOT NULL,
                    video_reference TEXT NOT NULL,
                    quality_preference TEXT NOT NULL,
                    requester_id TEXT NOT NULL,
                    session_proof TEXT NOT NULL,
                    entitlement_proof TEXT NOT NULL,
                    queue_status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    attempt_count INTEGER NOT NULL,
                    artifact_location TEXT,
                    error_code TEXT,
                    error_detail TEXT
                )
                """
            )

            columns = {
                str(row["name"]).lower()
                for row in self._connection.execute("PRAGMA table_info(download_jobs)").fetchall()
            }
            if "error_detail" not in columns:
                self._connection.execute("ALTER TABLE download_jobs ADD COLUMN error_detail TEXT")

            self._connection.commit()

    def _row_to_job(self, row: sqlite3.Row) -> DownloadJob:
        return DownloadJob(
            download_id=str(row["download_id"]),
            provider=str(row["provider"]),
            video_reference=str(row["video_reference"]),
            quality_preference=str(row["quality_preference"]),
            requester_id=str(row["requester_id"]),
            session_proof=str(row["session_proof"]),
            entitlement_proof=str(row["entitlement_proof"]),
            queue_status=str(row["queue_status"]),
            created_at=datetime.fromisoformat(str(row["created_at"])),
            updated_at=datetime.fromisoformat(str(row["updated_at"])),
            attempt_count=int(row["attempt_count"]),
            artifact_location=row["artifact_location"],
            error_code=row["error_code"],
            error_detail=row["error_detail"],
        )

    def create_if_absent(self, job: DownloadJob) -> tuple[DownloadJob, bool]:
        with self._lock:
            existing = self.get(job.download_id)
            if existing is not None:
                return existing, False

            self._connection.execute(
                """
                INSERT INTO download_jobs (
                    download_id,
                    provider,
                    video_reference,
                    quality_preference,
                    requester_id,
                    session_proof,
                    entitlement_proof,
                    queue_status,
                    created_at,
                    updated_at,
                    attempt_count,
                    artifact_location,
                    error_code,
                    error_detail
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    job.download_id,
                    job.provider,
                    job.video_reference,
                    job.quality_preference,
                    job.requester_id,
                    job.session_proof,
                    job.entitlement_proof,
                    job.queue_status,
                    job.created_at.isoformat(),
                    job.updated_at.isoformat(),
                    job.attempt_count,
                    job.artifact_location,
                    job.error_code,
                    job.error_detail,
                ),
            )
            self._connection.commit()
            return job, True

    def get(self, download_id: str) -> DownloadJob | None:
        with self._lock:
            row = self._connection.execute(
                "SELECT * FROM download_jobs WHERE download_id = ?",
                (download_id,),
            ).fetchone()
            if row is None:
                return None
            return self._row_to_job(row)

    def mark_processing(self, download_id: str) -> DownloadJob | None:
        with self._lock:
            job = self.get(download_id)
            if job is None:
                return None
            if job.queue_status in ("completed", "failed", "canceled"):
                return job

            updated = job.to_processing()
            self._connection.execute(
                """
                UPDATE download_jobs
                SET queue_status = ?, updated_at = ?, error_code = ?, error_detail = ?
                WHERE download_id = ?
                """,
                (
                    updated.queue_status,
                    updated.updated_at.isoformat(),
                    updated.error_code,
                    updated.error_detail,
                    download_id,
                ),
            )
            self._connection.commit()
            return updated

    def mark_completed(
        self,
        download_id: str,
        artifact_location: str | None,
        attempt_count: int,
    ) -> DownloadJob | None:
        with self._lock:
            job = self.get(download_id)
            if job is None:
                return None
            if job.queue_status in ("completed", "failed", "canceled"):
                return job

            updated = job.to_completed(
                artifact_location=artifact_location,
                attempt_count=attempt_count,
            )
            self._connection.execute(
                """
                UPDATE download_jobs
                SET queue_status = ?,
                    artifact_location = ?,
                    attempt_count = ?,
                    error_code = ?,
                    error_detail = ?,
                    updated_at = ?
                WHERE download_id = ?
                """,
                (
                    updated.queue_status,
                    updated.artifact_location,
                    updated.attempt_count,
                    updated.error_code,
                    updated.error_detail,
                    updated.updated_at.isoformat(),
                    download_id,
                ),
            )
            self._connection.commit()
            return updated

    def mark_failed(
        self,
        download_id: str,
        error_code: str,
        attempt_count: int,
        error_detail: str | None = None,
    ) -> DownloadJob | None:
        with self._lock:
            job = self.get(download_id)
            if job is None:
                return None
            if job.queue_status in ("completed", "failed", "canceled"):
                return job

            updated = job.to_failed(
                error_code=error_code,
                attempt_count=attempt_count,
                error_detail=error_detail,
            )
            self._connection.execute(
                """
                UPDATE download_jobs
                SET queue_status = ?,
                    error_code = ?,
                    error_detail = ?,
                    attempt_count = ?,
                    updated_at = ?
                WHERE download_id = ?
                """,
                (
                    updated.queue_status,
                    updated.error_code,
                    updated.error_detail,
                    updated.attempt_count,
                    updated.updated_at.isoformat(),
                    download_id,
                ),
            )
            self._connection.commit()
            return updated

    def mark_canceled(self, download_id: str, error_code: str) -> DownloadJob | None:
        with self._lock:
            job = self.get(download_id)
            if job is None:
                return None
            if job.queue_status in ("completed", "failed", "canceled"):
                return job

            updated = job.to_canceled(error_code=error_code)
            self._connection.execute(
                """
                UPDATE download_jobs
                SET queue_status = ?, error_code = ?, error_detail = ?, updated_at = ?
                WHERE download_id = ?
                """,
                (
                    updated.queue_status,
                    updated.error_code,
                    updated.error_detail,
                    updated.updated_at.isoformat(),
                    download_id,
                ),
            )
            self._connection.commit()
            return updated

    def prune_terminal_jobs(self, older_than: datetime) -> list[str]:
        threshold = older_than.isoformat()
        with self._lock:
            rows = self._connection.execute(
                """
                SELECT artifact_location
                FROM download_jobs
                WHERE queue_status IN ('completed', 'failed', 'canceled')
                  AND updated_at < ?
                """,
                (threshold,),
            ).fetchall()
            self._connection.execute(
                """
                DELETE FROM download_jobs
                WHERE queue_status IN ('completed', 'failed', 'canceled')
                  AND updated_at < ?
                """,
                (threshold,),
            )
            self._connection.commit()

        artifacts = [str(row["artifact_location"]) for row in rows if row["artifact_location"]]
        return artifacts

    def count_by_status(self) -> dict[str, int]:
        counters = {
            "queued": 0,
            "processing": 0,
            "completed": 0,
            "failed": 0,
            "canceled": 0,
        }
        with self._lock:
            rows = self._connection.execute(
                "SELECT queue_status, COUNT(*) AS count FROM download_jobs GROUP BY queue_status"
            ).fetchall()
        for row in rows:
            counters[str(row["queue_status"])] = int(row["count"])
        return counters

    def ping(self) -> bool:
        with self._lock:
            row = self._connection.execute("SELECT 1 AS ok").fetchone()
            if row is None:
                return False
            return int(row["ok"]) == 1

    def close(self) -> None:
        with self._lock:
            self._connection.close()

    def __del__(self) -> None:
        try:
            self.close()
        except Exception:
            return
