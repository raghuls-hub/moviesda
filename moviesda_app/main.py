from __future__ import annotations

import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from kivy.clock import Clock
from kivy.lang import Builder
from kivy.uix.screenmanager import ScreenManager
from kivymd.app import MDApp

from config import AppConfig
from models import DownloadJob, JobStatus, MoviePage, YearOption
from services.downloader import DownloadService
from services.queue_manager import DownloadQueueManager
from services.source import SeriesDetectedError, SourceService
from state import AppState
from ui.screens import DownloadScreen, MovieDetailScreen, MovieListScreen, YearSelectionScreen


class MovieBrowserApp(MDApp):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.config_data = AppConfig.from_env()
        self.state = AppState()
        self.source_service = SourceService(
            base_url=self.config_data.base_url,
            search_query=self.config_data.search_query,
            timeout=self.config_data.request_timeout,
        )
        self.download_service = DownloadService(
            download_dir=self.config_data.download_dir,
            timeout=self.config_data.request_timeout,
        )
        self.executor = ThreadPoolExecutor(max_workers=4)
        self.queue_manager = DownloadQueueManager(
            download_service=self.download_service,
            on_update=self._on_job_update,
        )

    def build(self):
        self.title = "MoviesDA App"
        self.theme_cls.theme_style = "Dark"
        self.theme_cls.primary_palette = "Blue"
        self.theme_cls.primary_hue = "400"
        self.theme_cls.accent_palette = "Amber"
        Builder.load_file(str(Path(__file__).resolve().parent / "ui" / "app.kv"))
        manager = ScreenManager()
        manager.add_widget(YearSelectionScreen(name="years"))
        manager.add_widget(MovieListScreen(name="movies"))
        manager.add_widget(MovieDetailScreen(name="detail"))
        manager.add_widget(DownloadScreen(name="download"))
        return manager

    def on_start(self):
        self.state.status_message = "Ready"

    def on_stop(self):
        # Signal the worker to stop after finishing the current job
        self.queue_manager.shutdown()

    # ---------------------------------------------------------------- queue

    def enqueue_download(self, url: str, title: str, referer: str | None = None) -> None:
        job = DownloadJob(
            id=str(uuid.uuid4()),
            title=title,
            url=url,
            referer=referer or self.state.base_url or "",
        )
        self.queue_manager.enqueue(job)  # _apply_job_update will sync state.download_jobs
        self.open_download_screen()

    def cancel_job(self, job_id: str) -> None:
        self.queue_manager.cancel(job_id)

    def _on_job_update(self, job: DownloadJob) -> None:
        Clock.schedule_once(lambda *_: self._apply_job_update(job))

    def _apply_job_update(self, job: DownloadJob) -> None:
        self.state.download_jobs = self.queue_manager.all_jobs()
        self._send_notification(job)
        if not self.root or self.root.current != "download":
            return
        screen = self.root.get_screen("download")
        if job.status == JobStatus.DOWNLOADING:
            screen.update_active_progress(job)
        else:
            screen.refresh()

    def _send_notification(self, job: DownloadJob) -> None:
        if job.status not in (JobStatus.DOWNLOADING, JobStatus.DONE, JobStatus.ERROR):
            return
        if not hasattr(self, "_last_notified_status"):
            self._last_notified_status: dict[str, str] = {}
        if job.status == JobStatus.DOWNLOADING and self._last_notified_status.get(job.id) == JobStatus.DOWNLOADING:
            return
        self._last_notified_status[job.id] = job.status
        # fire in a background thread so plyer never blocks the Kivy UI thread
        self.executor.submit(self._notify_worker, job.status, job.title, job.error)

    def _notify_worker(self, status: str, title: str, error: str) -> None:
        try:
            from plyer import notification  # noqa: PLC0415
            def _trunc(s: str, n: int = 60) -> str:
                return s if len(s) <= n else s[:n - 1] + "\u2026"
            if status == JobStatus.DOWNLOADING:
                notification.notify(title=_trunc("Downloading"), message=_trunc(title), app_name="MoviesDA", timeout=2)
            elif status == JobStatus.DONE:
                notification.notify(title=_trunc("Download complete"), message=_trunc(title), app_name="MoviesDA", timeout=4)
            elif status == JobStatus.ERROR:
                notification.notify(title=_trunc("Download failed"), message=_trunc(f"{title}: {error}"), app_name="MoviesDA", timeout=4)
        except Exception:  # noqa: BLE001
            pass

    # --------------------------------------------------------- navigation

    def open_download_screen(self) -> None:
        if not self.root:
            return
        if self.root.current != "download":
            self.state.last_screen = self.root.current
        self.root.current = "download"
        screen = self.root.get_screen("download")
        # if a download is already active, update in-place instead of full rebuild
        active = next((j for j in self.state.download_jobs if j.status == JobStatus.DOWNLOADING), None)
        if active:
            screen.update_active_progress(active)
        else:
            screen.refresh()

    def go_back_from_downloads(self) -> None:
        if not self.root:
            return
        target = self.state.last_screen or "movies"
        if target == "download":
            target = "movies"
        self.root.current = target

    # --------------------------------------------------------- async loaders

    def load_years_async(self, success, failure):
        def task():
            try:
                print("[years] Starting discovery of base URL...")
                base_url = self.source_service.discover_base_url()
                print(f"[years] discover_base_url -> {base_url}")
                if not base_url:
                    raise RuntimeError("Could not resolve a source URL. Set MOVIESDA_BASE_URL first.")
                self.state.base_url = base_url
                latest_year_link = self.source_service.get_latest_year_link(base_url)
                if not latest_year_link:
                    raise RuntimeError("Could not find a year index page.")
                home_html = self.source_service.resolve_to_home_html(latest_year_link, base_url)
                if not home_html:
                    raise RuntimeError("Could not resolve the home.html page.")
                self.state.home_html_url = home_html
                years = self.source_service.get_year_movie_links(home_html)
                self.state.years = [
                    YearOption(year=int(year), label=data["label"], url=data["url"])
                    for year, data in sorted(years.items(), key=lambda item: int(item[0]), reverse=True)
                ]
                Clock.schedule_once(lambda *_: success(self.state.years))
            except Exception as exc:  # noqa: BLE001
                err = exc
                Clock.schedule_once(lambda *_: failure(str(err)))

        self.executor.submit(task)

    def load_movies_async(self, year_url: str, page_index: int, success, failure):
        def task():
            try:
                page_data = self.source_service.list_movies(year_url, page_index=page_index, page_size=self.config_data.page_size)
                self.state.movies = page_data.movies
                self.state.current_site_page = page_data.current_page
                self.state.total_site_pages = page_data.total_pages
                self.state.available_pages = page_data.page_numbers
                self.state.current_page = max(page_data.current_page - 1, 0)
                Clock.schedule_once(lambda *_: success(page_data))
            except Exception as exc:  # noqa: BLE001
                err = exc
                Clock.schedule_once(lambda *_: failure(str(err)))

        self.executor.submit(task)

    def load_movie_detail_fast_async(self, movie_url: str, success, failure):
        def task():
            try:
                detail = self.source_service.get_movie_detail_fast(movie_url, self.state.base_url or movie_url)
                Clock.schedule_once(lambda *_: success(detail))
            except Exception as exc:  # noqa: BLE001
                err = exc
                Clock.schedule_once(lambda *_: failure(str(err)))
        self.executor.submit(task)

    def fetch_download_links_async(self, movie_url: str, success, failure, on_series=None):
        def task():
            try:
                links = self.source_service.fetch_download_links(movie_url, self.state.base_url or movie_url)
                Clock.schedule_once(lambda *_: success(links))
            except SeriesDetectedError as exc:
                msg = str(exc)
                if on_series:
                    Clock.schedule_once(lambda *_: on_series(msg))
                else:
                    Clock.schedule_once(lambda *_: failure(msg))
            except Exception as exc:  # noqa: BLE001
                err = exc
                Clock.schedule_once(lambda *_: failure(str(err)))
        self.executor.submit(task)

    def load_movie_detail_async(self, movie_url: str, success, failure):
        def task():
            try:
                detail = self.source_service.get_movie_detail(movie_url, self.state.base_url or movie_url)
                Clock.schedule_once(lambda *_: success(detail))
            except Exception as exc:  # noqa: BLE001
                err = exc
                Clock.schedule_once(lambda *_: failure(str(err)))

        self.executor.submit(task)


def main() -> None:
    MovieBrowserApp().run()


if __name__ == "__main__":
    main()
