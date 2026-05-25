from __future__ import annotations

from functools import partial

from kivy.metrics import dp
from kivy.uix.image import AsyncImage
from kivy.uix.progressbar import ProgressBar
from kivy.uix.screenmanager import Screen
from kivymd.app import MDApp
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.button import MDButton, MDButtonText, MDIconButton
from kivymd.uix.card import MDCard
from kivymd.uix.label import MDLabel

from moviesda_app.models import DownloadJob, JobStatus, MovieCard, MovieDetail, MoviePage, YearOption


class BaseContentScreen(Screen):
    def clear_content(self) -> None:
        self.ids.content.clear_widgets()

    def set_status(self, message: str) -> None:
        self.ids.status.text = message


class YearSelectionScreen(BaseContentScreen):
    def on_pre_enter(self, *args):
        self.load_years()

    def load_years(self):
        app = MDApp.get_running_app()
        self.clear_content()
        self.set_status("Loading years...")
        app.load_years_async(self.render_years, self.show_error)

    def render_years(self, years: list[YearOption]) -> None:
        self.clear_content()
        self.set_status(f"Found {len(years)} year group(s)")
        if not years:
            self.ids.content.add_widget(MDLabel(text="No year pages were found.", halign="center"))
            return
        for year in years:
            card = MDCard(
                padding=dp(14),
                radius=[dp(18), dp(18), dp(18), dp(18)],
                size_hint_y=None,
                height=dp(88),
                md_bg_color=(0.10, 0.12, 0.16, 1),
            )
            row = MDBoxLayout(orientation="horizontal", spacing=dp(12))
            text_box = MDBoxLayout(orientation="vertical")
            text_box.add_widget(MDLabel(text=str(year.year), bold=True, text_color=(1, 1, 1, 1)))
            text_box.add_widget(MDLabel(text=year.label, theme_text_color="Secondary", shorten=True, text_color=(0.75, 0.85, 1, 1)))
            button = MDButton(md_bg_color=(0.13, 0.39, 0.85, 1))
            button.add_widget(MDButtonText(text="Open"))
            button.bind(on_release=partial(self.open_year, year))
            row.add_widget(text_box)
            row.add_widget(button)
            card.add_widget(row)
            self.ids.content.add_widget(card)

    def open_year(self, year: YearOption, *_args) -> None:
        app = MDApp.get_running_app()
        app.state.selected_year = year
        app.state.current_page = 0
        app.root.current = "movies"
        app.root.get_screen("movies").load_movies()

    def show_error(self, message: str) -> None:
        self.clear_content()
        self.set_status(message)
        self.ids.content.add_widget(MDLabel(text=message, halign="center", text_color=(1, 0.68, 0.68, 1)))


class MovieListScreen(BaseContentScreen):
    def on_pre_enter(self, *args):
        if not MDApp.get_running_app().state.selected_year:
            MDApp.get_running_app().root.current = "years"
            return
        self.load_movies()

    def load_movies(self):
        app = MDApp.get_running_app()
        year = app.state.selected_year
        if not year:
            return
        self.clear_content()
        self.set_status(f"Loading movies for {year.year}...")
        app.load_movies_async(year.url, app.state.current_page, self.render_movies, self.show_error)

    def render_movies(self, page_data: MoviePage) -> None:
        app = MDApp.get_running_app()
        self.clear_content()
        self.set_status(f"Page {page_data.current_page} of {page_data.total_pages}")
        movies = page_data.movies
        if not movies:
            self.ids.content.add_widget(MDLabel(text="No movies found on this page.", halign="center", text_color=(0.8, 0.9, 1, 1)))
            return

        grid = MDBoxLayout(orientation="vertical", spacing=dp(12), size_hint_y=None)
        grid.bind(minimum_height=grid.setter("height"))
        for movie in movies:
            grid.add_widget(self._build_movie_card(movie))
        self.ids.content.add_widget(grid)
        self.ids.content.add_widget(self._build_pagination_section())

    def _top_controls(self) -> MDBoxLayout:
        # kept for potential future use
        app = MDApp.get_running_app()
        bar = MDBoxLayout(orientation="horizontal", size_hint_y=None, height=dp(44), spacing=dp(8))
        downloads = MDButton(md_bg_color=(0.13, 0.39, 0.85, 1), size_hint_x=None, width=dp(140))
        downloads.add_widget(MDButtonText(text="Downloads"))
        downloads.bind(on_release=lambda *_: app.open_download_screen())
        bar.add_widget(downloads)
        return bar

    def _build_pagination_section(self) -> MDBoxLayout:
        app = MDApp.get_running_app()
        current = app.state.current_site_page
        total = app.state.total_site_pages
        available = app.state.available_pages or list(range(1, total + 1))

        section = MDBoxLayout(orientation="vertical", spacing=dp(8), size_hint_y=None, adaptive_height=True, padding=(0, dp(8), 0, dp(8)))
        section.add_widget(MDLabel(text="Pages", bold=True, halign="center", size_hint_y=None, height=dp(24), text_color=(0.9, 0.95, 1, 1)))

        # outer box fills full width; inner row is shrunk to content and centered
        outer = MDBoxLayout(orientation="horizontal", size_hint_y=None, height=dp(44))
        outer.add_widget(MDLabel(size_hint_x=1))  # left spacer
        row = MDBoxLayout(orientation="horizontal", spacing=dp(8), size_hint_x=None, size_hint_y=None, height=dp(44))
        row.bind(minimum_width=row.setter("width"))

        row.add_widget(self._page_button("Prev", max(current - 1, 1), enabled=current > 1))

        window = [p for p in available if abs(p - current) <= 2]
        if 1 in available and 1 not in window:
            window = [1] + window
        if total in available and total not in window:
            window = window + [total]

        for page in window:
            is_current = page == current
            row.add_widget(self._page_button(str(page), page, enabled=not is_current, active=is_current))

        row.add_widget(self._page_button("Next", min(current + 1, total), enabled=current < total))
        outer.add_widget(row)
        outer.add_widget(MDLabel(size_hint_x=1))  # right spacer
        section.add_widget(outer)
        return section

    def _page_button(self, label: str, page_number: int, *, enabled: bool = True, active: bool = False) -> MDButton:
        button = MDButton(md_bg_color=(0.18, 0.57, 0.87, 1) if active else (0.13, 0.39, 0.85, 1))
        button.disabled = not enabled
        button.add_widget(MDButtonText(text=label))
        if enabled:
            button.bind(on_release=lambda *_: self.go_to_page(page_number))
        return button

    def go_to_page(self, page_number: int) -> None:
        app = MDApp.get_running_app()
        app.state.current_page = max(page_number - 1, 0)
        self.load_movies()

    def _build_movie_card(self, movie: MovieCard) -> MDCard:
        card = MDCard(radius=[dp(18), dp(18), dp(18), dp(18)], size_hint_y=None, height=dp(100), padding=dp(10), md_bg_color=(0.10, 0.12, 0.16, 1))
        horizontal = MDBoxLayout(orientation="horizontal", spacing=dp(8))
        horizontal.add_widget(MDLabel(text=movie.title, bold=True, halign="center", shorten=True, size_hint_y=None, height=dp(36), text_color=(1, 1, 1, 1)))
        action = MDButton(md_bg_color=(0.18, 0.57, 0.87, 1))
        action.add_widget(MDButtonText(text="Details"))
        action.bind(on_release=partial(self.open_detail, movie))
        horizontal.add_widget(action)
        card.add_widget(horizontal)
        return card

    def open_detail(self, movie: MovieCard, *_args) -> None:
        app = MDApp.get_running_app()
        app.root.get_screen("detail").load_movie(movie)
        app.root.current = "detail"

    def previous_page(self):
        app = MDApp.get_running_app()
        if app.state.current_site_page > 1:
            app.state.current_page = app.state.current_site_page - 2
            self.load_movies()

    def next_page(self):
        app = MDApp.get_running_app()
        if app.state.current_site_page < app.state.total_site_pages:
            app.state.current_page = app.state.current_site_page
            self.load_movies()

    def show_error(self, message: str) -> None:
        self.clear_content()
        self.set_status(message)
        self.ids.content.add_widget(MDLabel(text=message, halign="center", text_color=(1, 0.68, 0.68, 1)))


class MovieDetailScreen(BaseContentScreen):
    def load_movie(self, movie: MovieCard) -> None:
        app = MDApp.get_running_app()
        self._current_movie = movie
        self._movie_url = movie.url
        self._links_container: MDBoxLayout | None = None
        self.clear_content()
        self.set_status("Loading...")
        app.load_movie_detail_fast_async(movie.url, self.render_detail, self.show_error)

    def refresh(self) -> None:
        if hasattr(self, "_current_movie") and self._current_movie:
            self.load_movie(self._current_movie)

    def render_detail(self, detail: MovieDetail) -> None:
        app = MDApp.get_running_app()
        app.state.movie_detail = detail
        self.clear_content()
        self.set_status(detail.title)
        wrapper = MDBoxLayout(orientation="vertical", spacing=dp(16), adaptive_height=True)

        if detail.poster_url:
            wrapper.add_widget(AsyncImage(source=detail.poster_url, size_hint_y=None, height=dp(320)))
        wrapper.add_widget(MDLabel(text=detail.title, bold=True, halign="center", size_hint_y=None, height=dp(42), text_color=(1, 1, 1, 1)))
        if detail.synopsis:
            wrapper.add_widget(MDLabel(text=detail.synopsis, adaptive_height=True, halign="center", text_color=(0.9, 0.9, 0.9, 1)))
        if detail.metadata:
            for key, value in detail.metadata.items():
                wrapper.add_widget(MDLabel(text=f"{key}: {value}", adaptive_height=True, halign="center", text_color=(0.8, 0.9, 1, 1)))

        # centered "Generate Download Links" button
        btn_row = MDBoxLayout(orientation="horizontal", size_hint_y=None, height=dp(48))
        btn_row.add_widget(MDLabel(size_hint_x=1))
        gen_btn = MDButton(md_bg_color=(0.13, 0.55, 0.13, 1))
        gen_btn.add_widget(MDButtonText(text="Generate Download Links"))
        gen_btn.bind(on_release=self._on_generate_links)
        btn_row.add_widget(gen_btn)
        btn_row.add_widget(MDLabel(size_hint_x=1))
        wrapper.add_widget(btn_row)

        self._links_container = MDBoxLayout(orientation="vertical", spacing=dp(8), adaptive_height=True)
        wrapper.add_widget(self._links_container)
        self.ids.content.add_widget(wrapper)

    def _on_generate_links(self, *_args) -> None:
        app = MDApp.get_running_app()
        if not self._links_container:
            return
        self._links_container.clear_widgets()
        self._links_container.add_widget(
            MDLabel(text="Generating links, please wait...", halign="center",
                    text_color=(0.78, 0.86, 1, 1), size_hint_y=None, height=dp(32))
        )
        app.fetch_download_links_async(
            self._movie_url,
            self._render_links,
            self._links_error,
            on_series=self._on_series_detected,
        )

    def _on_series_detected(self, message: str) -> None:
        if not self._links_container:
            return
        self._links_container.clear_widgets()
        self._links_container.add_widget(
            MDLabel(
                text="⚠ This is not a movie, it is a series.",
                halign="center",
                adaptive_height=True,
                text_color=(1, 0.2, 0.2, 1),
                bold=True,
            )
        )

    def _render_links(self, links: list) -> None:
        if not self._links_container:
            return
        self._links_container.clear_widgets()
        if not links:
            self._links_container.add_widget(
                MDLabel(text="No download links found.", halign="center", text_color=(1, 0.6, 0.6, 1))
            )
            return
        self._links_container.add_widget(
            MDLabel(text="Download Links", bold=True, halign="center", size_hint_y=None, height=dp(28), text_color=(1, 0.85, 0.3, 1))
        )
        for link in links:
            size_str = self._fmt_size(link.file_size_bytes)
            row = MDBoxLayout(orientation="horizontal", size_hint_y=None, height=dp(56), spacing=dp(8), padding=(dp(4), 0))
            info = MDBoxLayout(orientation="vertical")
            info.add_widget(MDLabel(text=link.label, text_color=(1, 1, 1, 1), shorten=True, halign="center", size_hint_y=None, height=dp(28)))
            info.add_widget(MDLabel(text=size_str, text_color=(0.6, 0.85, 1, 1), halign="center", size_hint_y=None, height=dp(22)))
            row.add_widget(info)
            dl_icon = MDIconButton(
                icon="download",
                theme_text_color="Custom",
                text_color=(0.18, 0.57, 0.87, 1),
                size_hint_x=None,
                width=dp(48),
            )
            dl_icon.bind(on_release=partial(self._queue_link, link.url, link.label))
            row.add_widget(dl_icon)
            self._links_container.add_widget(row)

    def _links_error(self, message: str) -> None:
        if not self._links_container:
            return
        self._links_container.clear_widgets()
        self._links_container.add_widget(
            MDLabel(text=f"Error: {message}", halign="center", text_color=(1, 0.5, 0.5, 1))
        )

    def _queue_link(self, url: str, label: str, *_args) -> None:
        app = MDApp.get_running_app()
        self.set_status(f"Queued: {label}")
        app.enqueue_download(url, label)
        app.open_download_screen()

    def _fmt_size(self, size: int) -> str:
        if size <= 0:
            return "Size unknown"
        units = ["B", "KB", "MB", "GB"]
        s = float(size)
        for unit in units:
            if s < 1024.0 or unit == units[-1]:
                return f"{s:.1f} {unit}"
            s /= 1024.0
        return f"{s:.1f} GB"  # unreachable but satisfies return type

    def show_error(self, message: str) -> None:
        self.clear_content()
        self.set_status(message)
        self.ids.content.add_widget(MDLabel(text=message, halign="center", text_color=(1, 0.68, 0.68, 1)))


class DownloadScreen(BaseContentScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._active_job_id: str | None = None
        self._progress_bar: ProgressBar | None = None
        self._progress_label: MDLabel | None = None

    def on_pre_enter(self, *args):
        self.refresh()

    def refresh(self) -> None:
        """Full rebuild — only called on structural changes (new job, completion, cancel)."""
        app = MDApp.get_running_app()
        jobs = app.state.download_jobs
        self.clear_content()
        self._progress_bar = None
        self._progress_label = None
        self._active_job_id = None

        active = next((j for j in jobs if j.status == JobStatus.DOWNLOADING), None)
        pending = [j for j in jobs if j.status == JobStatus.PENDING]
        done = [j for j in jobs if j.status in (JobStatus.DONE, JobStatus.CANCELLED, JobStatus.ERROR)]

        if not jobs:
            self.ids.content.add_widget(MDLabel(text="No downloads yet.", halign="center", text_color=(0.8, 0.9, 1, 1)))
            return

        if active:
            card, bar, label = self._active_card(active)
            self._active_job_id = active.id
            self._progress_bar = bar
            self._progress_label = label
            self.ids.content.add_widget(card)

        if pending:
            self.ids.content.add_widget(MDLabel(text="Queue", bold=True, size_hint_y=None, height=dp(28), text_color=(1, 0.85, 0.3, 1)))
            for job in pending:
                self.ids.content.add_widget(self._queue_card(job))

        if done:
            self.ids.content.add_widget(MDLabel(text="Completed", bold=True, size_hint_y=None, height=dp(28), text_color=(0.6, 0.9, 0.6, 1)))
            for job in reversed(done):
                self.ids.content.add_widget(self._done_card(job))

    def update_active_progress(self, job: DownloadJob) -> None:
        """Update only the progress bar and label in-place — no widget rebuild."""
        if job.id != self._active_job_id or self._progress_bar is None or self._progress_label is None:
            # Structure changed (new active job or job finished) — do full rebuild
            self.refresh()
            return
        self._progress_bar.value = job.percent
        self._progress_label.text = f"{job.percent:.1f}%  —  {self._fmt(job.downloaded_bytes)} / {self._fmt(job.total_bytes)}"

    def _active_card(self, job: DownloadJob) -> tuple[MDCard, ProgressBar, MDLabel]:
        card = MDCard(md_bg_color=(0.10, 0.12, 0.16, 1), radius=[dp(14)] * 4, padding=dp(14), size_hint_y=None)
        card.bind(minimum_height=card.setter("height"))
        col = MDBoxLayout(orientation="vertical", spacing=dp(8), size_hint_y=None)
        col.bind(minimum_height=col.setter("height"))

        header = MDBoxLayout(orientation="horizontal", size_hint_y=None, height=dp(36))
        header.add_widget(MDLabel(text=job.title, bold=True, text_color=(1, 1, 1, 1), shorten=True))
        cancel_btn = MDButton(md_bg_color=(0.75, 0.18, 0.18, 1), size_hint_x=None, width=dp(90))
        cancel_btn.add_widget(MDButtonText(text="Cancel"))
        cancel_btn.bind(on_release=partial(self._cancel_job, job.id))
        header.add_widget(cancel_btn)
        col.add_widget(header)

        bar = ProgressBar(max=100, value=job.percent, size_hint_y=None, height=dp(14))
        pct_label = MDLabel(
            text=f"{job.percent:.1f}%  —  {self._fmt(job.downloaded_bytes)} / {self._fmt(job.total_bytes)}",
            halign="center", text_color=(1, 0.85, 0.3, 1), size_hint_y=None, height=dp(24),
        )
        col.add_widget(bar)
        col.add_widget(pct_label)
        card.add_widget(col)
        return card, bar, pct_label

    def _queue_card(self, job: DownloadJob) -> MDCard:
        card = MDCard(md_bg_color=(0.10, 0.14, 0.20, 1), radius=[dp(10)] * 4, padding=dp(10),
                      size_hint_y=None, height=dp(52))
        row = MDBoxLayout(orientation="horizontal", spacing=dp(8))
        row.add_widget(MDIconButton(icon="clock-outline", theme_text_color="Custom", text_color=(0.6, 0.7, 1, 1)))
        row.add_widget(MDLabel(text=job.title, text_color=(0.85, 0.9, 1, 1), shorten=True))
        cancel_btn = MDButton(md_bg_color=(0.5, 0.15, 0.15, 1), size_hint_x=None, width=dp(80))
        cancel_btn.add_widget(MDButtonText(text="Remove"))
        cancel_btn.bind(on_release=partial(self._cancel_job, job.id))
        row.add_widget(cancel_btn)
        card.add_widget(row)
        return card

    def _done_card(self, job: DownloadJob) -> MDCard:
        is_error = job.status == JobStatus.ERROR
        is_cancelled = job.status == JobStatus.CANCELLED
        color = (1, 0.4, 0.4, 1) if is_error else (0.6, 0.6, 0.6, 1) if is_cancelled else (0.4, 0.9, 0.5, 1)
        icon = "alert-circle" if is_error else "cancel" if is_cancelled else "check-circle"
        card = MDCard(md_bg_color=(0.08, 0.10, 0.14, 1), radius=[dp(10)] * 4, padding=dp(10),
                      size_hint_y=None, height=dp(52))
        row = MDBoxLayout(orientation="horizontal", spacing=dp(8))
        row.add_widget(MDIconButton(icon=icon, theme_text_color="Custom", text_color=color))
        label = job.error if is_error else job.title
        row.add_widget(MDLabel(text=label, text_color=color, shorten=True))
        card.add_widget(row)
        return card

    def _cancel_job(self, job_id: str, *_args) -> None:
        MDApp.get_running_app().cancel_job(job_id)

    def _fmt(self, value: int) -> str:
        if value <= 0:
            return "?"
        units = ["B", "KB", "MB", "GB"]
        size = float(value)
        for unit in units:
            if size < 1024.0 or unit == units[-1]:
                return f"{size:.1f} {unit}"
            size /= 1024.0
