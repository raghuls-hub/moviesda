from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

from kivy.clock import Clock
from kivy.lang import Builder
from kivy.uix.screenmanager import ScreenManager
from kivymd.app import MDApp
from pathlib import Path
from moviesda_app.config import AppConfig
from moviesda_app.models import DownloadProgress, MoviePage, YearOption
from moviesda_app.services.downloader import DownloadService
from moviesda_app.services.source import SourceService
from moviesda_app.state import AppState
from moviesda_app.ui.screens import DownloadScreen, MovieDetailScreen, MovieListScreen, YearSelectionScreen


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

    def build(self):
        self.title = "MoviesDA App"
        # Professional dark theme with strong contrast and blue/gold accents
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

    def load_years_async(self, success, failure):
        def task():
            try:
                print("[years] Starting discovery of base URL...")
                base_url = self.source_service.discover_base_url()
                print(f"[years] discover_base_url -> {base_url}")
                if not base_url:
                    raise RuntimeError("Could not resolve a source URL. Set MOVIESDA_BASE_URL first.")
                self.state.base_url = base_url
                print(f"[years] Fetching latest year link from {base_url}...")
                latest_year_link = self.source_service.get_latest_year_link(base_url)
                print(f"[years] get_latest_year_link -> {latest_year_link}")
                if not latest_year_link:
                    raise RuntimeError("Could not find a year index page.")
                print(f"[years] Resolving home.html from {latest_year_link}...")
                home_html = self.source_service.resolve_to_home_html(latest_year_link, base_url)
                print(f"[years] resolve_to_home_html -> {home_html}")
                if not home_html:
                    raise RuntimeError("Could not resolve the home.html page.")
                self.state.home_html_url = home_html
                print(f"[years] Getting year links from {home_html}...")
                years = self.source_service.get_year_movie_links(home_html)
                print(f"[years] get_year_movie_links -> found {len(years)} entries")
                self.state.years = [
                    YearOption(year=int(year), label=data["label"], url=data["url"])
                    for year, data in sorted(years.items(), key=lambda item: int(item[0]), reverse=True)
                ]
                print(f"[years] Prepared {len(self.state.years)} YearOption objects")
                for y in self.state.years:
                    print(f"[years]  - {y.year}: {y.label} -> {y.url}")
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

    def open_download_screen(self) -> None:
        if not self.root:
            return
        if self.root.current != "download":
            self.state.last_screen = self.root.current
        self.root.current = "download"
        self._refresh_download_screen()

    def go_back_from_downloads(self) -> None:
        if not self.root:
            return
        target = self.state.last_screen or "movies"
        if target == "download":
            target = "movies"
        self.root.current = target

    def start_download(self, url: str, title: str, referer: str | None = None) -> None:
        self.state.download_progress = DownloadProgress(title=title, url=url, status="Starting download...", percent=0.0, downloaded_bytes=0, total_bytes=0, file_path="", completed=False)
        self.open_download_screen()

        def progress_callback(downloaded_bytes: int, total_bytes: int) -> None:
            percent = (downloaded_bytes / total_bytes * 100) if total_bytes else 0.0
            progress = DownloadProgress(
                title=title,
                url=url,
                status=f"Downloading {title}...",
                percent=percent,
                downloaded_bytes=downloaded_bytes,
                total_bytes=total_bytes,
                file_path=self.state.download_progress.file_path,
                completed=False,
            )
            Clock.schedule_once(lambda *_: self._apply_download_progress(progress))

        def task():
            try:
                result = self.download_service.resolve_and_download(
                    url,
                    referer=referer or self.state.base_url or None,
                    progress_callback=progress_callback,
                )
                progress = DownloadProgress(
                    title=title,
                    url=url,
                    status="Download complete",
                    percent=100.0,
                    downloaded_bytes=result.size_bytes,
                    total_bytes=max(result.size_bytes, 1),
                    file_path=str(result.file_path),
                    completed=True,
                )
                Clock.schedule_once(lambda *_: self._apply_download_complete(progress))
            except Exception as exc:  # noqa: BLE001
                err = str(exc)
                progress = DownloadProgress(title=title, url=url, status=f"Error: {err}", percent=0.0, completed=False)
                Clock.schedule_once(lambda *_: self._apply_download_error(err, progress))

        self.executor.submit(task)

    def _refresh_download_screen(self) -> None:
        if self.root and "download" in self.root.screen_names:
            self.root.get_screen("download").render_download_state()

    def _apply_download_progress(self, progress: DownloadProgress) -> None:
        self.state.download_progress = progress
        if self.root and self.root.current == "download":
            self.root.get_screen("download").update_progress(progress)

    def _apply_download_complete(self, progress: DownloadProgress) -> None:
        self.state.download_progress = progress
        if self.root and self.root.current == "download":
            self.root.get_screen("download").show_complete(progress)

    def _apply_download_error(self, message: str, progress: DownloadProgress) -> None:
        self.state.download_progress = progress
        if self.root and self.root.current == "download":
            self.root.get_screen("download").show_error(message)

    def load_movie_detail_async(self, movie_url: str, success, failure):
        def task():
            try:
                detail = self.source_service.get_movie_detail(movie_url, self.state.base_url or movie_url)
                Clock.schedule_once(lambda *_: success(detail))
            except Exception as exc:  # noqa: BLE001
                err = exc
                Clock.schedule_once(lambda *_: failure(str(err)))

        self.executor.submit(task)

    def download_async(self, url: str, success, failure):
        def task():
            try:
                result = self.download_service.resolve_and_download(url, referer=self.state.base_url or None)
                message = f"Downloaded to {result.file_path}"
                Clock.schedule_once(lambda *_: success(message))
            except Exception as exc:  # noqa: BLE001
                err = exc
                Clock.schedule_once(lambda *_: failure(str(err)))

        self.executor.submit(task)


def main() -> None:
    MovieBrowserApp().run()
