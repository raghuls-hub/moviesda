from __future__ import annotations

import queue
import threading
from pathlib import Path
from typing import Callable

from moviesda_app.models import DownloadJob, JobStatus


class DownloadQueueManager:
    """Single-worker sequential download queue that survives app backgrounding."""

    def __init__(self, download_service, on_update: Callable[[DownloadJob], None]) -> None:
        self._service = download_service
        self._on_update = on_update
        self._queue: queue.Queue[DownloadJob] = queue.Queue()
        self._jobs: dict[str, DownloadJob] = {}
        self._lock = threading.Lock()
        self._cancel_active = threading.Event()
        self._active_id: str | None = None
        # non-daemon so downloads survive app backgrounding
        self._worker = threading.Thread(target=self._run, daemon=False, name="download-worker")
        self._worker.start()

    # ------------------------------------------------------------------ public

    def enqueue(self, job: DownloadJob) -> None:
        with self._lock:
            self._jobs[job.id] = job
        self._queue.put(job)
        self._on_update(job)

    def cancel(self, job_id: str) -> None:
        notify_job = None
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                return
            if job.status == JobStatus.DOWNLOADING and self._active_id == job_id:
                self._cancel_active.set()
                return
            if job.status == JobStatus.PENDING:
                updated = DownloadJob(
                    id=job.id, title=job.title, url=job.url, referer=job.referer,
                    status=JobStatus.CANCELLED, percent=job.percent,
                    downloaded_bytes=job.downloaded_bytes, total_bytes=job.total_bytes,
                    file_path=job.file_path, error=job.error,
                )
                self._jobs[job_id] = updated
                notify_job = updated
        if notify_job:
            self._on_update(notify_job)

    def all_jobs(self) -> list[DownloadJob]:
        with self._lock:
            return list(self._jobs.values())

    def shutdown(self) -> None:
        """Signal the worker to exit after finishing the current job."""
        self._queue.put(None)  # type: ignore[arg-type]  # sentinel

    # ----------------------------------------------------------------- private

    def _run(self) -> None:
        while True:
            job = self._queue.get()
            if job is None:  # shutdown sentinel
                self._queue.task_done()
                return
            with self._lock:
                current = self._jobs.get(job.id)
            if current is None or current.status == JobStatus.CANCELLED:
                self._queue.task_done()
                continue
            self._process(current)
            self._queue.task_done()

    def _process(self, job: DownloadJob) -> None:
        self._cancel_active.clear()
        self._active_id = job.id
        active_file: list[str] = []  # mutable cell so closure can write to it

        job = self._replace(job, status=JobStatus.DOWNLOADING)
        self._on_update(job)

        def progress_cb(downloaded: int, total: int) -> None:
            if self._cancel_active.is_set():
                raise InterruptedError
            percent = (downloaded / total * 100) if total else 0.0
            with self._lock:
                current = self._jobs.get(job.id, job)
            updated = self._replace(current, percent=percent, downloaded_bytes=downloaded, total_bytes=total)
            self._on_update(updated)

        def on_file_open(path: str) -> None:
            active_file.clear()
            active_file.append(path)
            with self._lock:
                current = self._jobs.get(job.id, job)
                updated = DownloadJob(
                    id=current.id, title=current.title, url=current.url, referer=current.referer,
                    status=current.status, percent=current.percent,
                    downloaded_bytes=current.downloaded_bytes, total_bytes=current.total_bytes,
                    file_path=path, error=current.error,
                )
                self._jobs[job.id] = updated

        try:
            result = self._service.resolve_and_download(
                job.url,
                referer=job.referer or None,
                progress_callback=progress_cb,
                on_file_open=on_file_open,
            )
            if self._cancel_active.is_set():
                Path(result.file_path).unlink(missing_ok=True)
                finished = self._replace(job, status=JobStatus.CANCELLED, percent=0.0)
            else:
                finished = self._replace(
                    job,
                    status=JobStatus.DONE,
                    percent=100.0,
                    downloaded_bytes=result.size_bytes,
                    total_bytes=result.size_bytes,
                    file_path=str(result.file_path),
                )
        except InterruptedError:
            if active_file:
                Path(active_file[0]).unlink(missing_ok=True)
            finished = self._replace(job, status=JobStatus.CANCELLED, percent=0.0)
        except Exception as exc:  # noqa: BLE001
            finished = self._replace(job, status=JobStatus.ERROR, error=str(exc))

        self._active_id = None
        self._on_update(finished)

    def _replace(self, job: DownloadJob, **kwargs) -> DownloadJob:
        updated = DownloadJob(
            id=job.id,
            title=kwargs.get("title", job.title),
            url=kwargs.get("url", job.url),
            referer=kwargs.get("referer", job.referer),
            status=kwargs.get("status", job.status),
            percent=kwargs.get("percent", job.percent),
            downloaded_bytes=kwargs.get("downloaded_bytes", job.downloaded_bytes),
            total_bytes=kwargs.get("total_bytes", job.total_bytes),
            file_path=kwargs.get("file_path", job.file_path),
            error=kwargs.get("error", job.error),
        )
        with self._lock:
            self._jobs[job.id] = updated
        return updated
