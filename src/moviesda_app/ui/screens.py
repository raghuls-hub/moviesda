from __future__ import annotations

from functools import partial

from kivy.metrics import dp
from kivy.uix.gridlayout import GridLayout
from kivy.uix.image import AsyncImage
from kivy.uix.progressbar import ProgressBar
from kivy.uix.screenmanager import Screen
from kivymd.app import MDApp
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.button import MDButton, MDButtonText, MDIconButton
from kivymd.uix.card import MDCard
from kivymd.uix.label import MDLabel

from moviesda_app.models import DownloadProgress, MovieCard, MovieDetail, MoviePage, YearOption


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

        grid = GridLayout(cols=2, spacing=dp(12), size_hint_y=None)
        grid.bind(minimum_height=grid.setter("height"))
        for movie in movies:
            grid.add_widget(self._build_movie_card(movie))
        self.ids.content.add_widget(grid)
        self.ids.content.add_widget(self._build_pagination_section())

    def _top_controls(self) -> MDBoxLayout:
        app = MDApp.get_running_app()
        bar = MDBoxLayout(orientation="horizontal", size_hint_y=None, height=dp(44), spacing=dp(8))
        spacer = MDLabel(text="", size_hint_x=1)
        downloads = MDButton(md_bg_color=(0.13, 0.39, 0.85, 1), size_hint_x=None, width=dp(140))
        downloads.add_widget(MDButtonText(text="Downloads"))
        downloads.bind(on_release=lambda *_: app.open_download_screen())
        bar.add_widget(spacer)
        bar.add_widget(downloads)
        return bar

    def _build_pagination_section(self) -> MDBoxLayout:
        app = MDApp.get_running_app()
        current = app.state.current_site_page
        total = app.state.total_site_pages
        available = app.state.available_pages or list(range(1, total + 1))

        section = MDBoxLayout(orientation="vertical", spacing=dp(8), size_hint_y=None, adaptive_height=True, padding=(0, dp(8), 0, dp(8)))
        section.add_widget(MDLabel(text="Pages", bold=True, halign="center", size_hint_y=None, height=dp(24), text_color=(0.9, 0.95, 1, 1)))

        row = MDBoxLayout(orientation="horizontal", spacing=dp(8), size_hint_y=None, height=dp(44))
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
        section.add_widget(row)
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
        card = MDCard(radius=[dp(18), dp(18), dp(18), dp(18)], size_hint_y=None, height=dp(280), padding=dp(10), md_bg_color=(0.10, 0.12, 0.16, 1))
        column = MDBoxLayout(orientation="vertical", spacing=dp(8))
        if movie.poster_url:
            column.add_widget(AsyncImage(source=movie.poster_url, size_hint_y=None, height=dp(170)))
        else:
            column.add_widget(MDLabel(text="[Poster]", markup=True, halign="center", size_hint_y=None, height=dp(170), text_color=(0.9, 0.9, 0.9, 1)))
        column.add_widget(MDLabel(text=movie.title, bold=True, halign="center", shorten=True, size_hint_y=None, height=dp(36), text_color=(1, 1, 1, 1)))
        action = MDButton(md_bg_color=(0.18, 0.57, 0.87, 1))
        action.add_widget(MDButtonText(text="Details"))
        action.bind(on_release=partial(self.open_detail, movie))
        column.add_widget(action)
        card.add_widget(column)
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
        self.clear_content()
        self.set_status("Loading movie details...")
        app.load_movie_detail_async(movie.url, self.render_detail, self.show_error)

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
            wrapper.add_widget(MDLabel(text=detail.synopsis, theme_text_color="Secondary", adaptive_height=True, text_color=(0.9, 0.9, 0.9, 1)))
        if detail.metadata:
            for key, value in detail.metadata.items():
                wrapper.add_widget(MDLabel(text=f"{key}: {value}", adaptive_height=True, text_color=(0.8, 0.9, 1, 1)))
        if detail.links:
            wrapper.add_widget(MDLabel(text="Download links", bold=True, size_hint_y=None, height=dp(28), text_color=(1, 0.85, 0.3, 1)))
            for link in detail.links:
                row = MDBoxLayout(orientation="horizontal", size_hint_y=None, height=dp(44), spacing=dp(8))
                row.add_widget(MDLabel(text=link.label, text_color=(1, 1, 1, 1)))
                icon = MDIconButton(icon="download", theme_text_color="Custom", text_color=(0.18, 0.57, 0.87, 1))
                icon.bind(on_release=partial(self.download_link, link.url, link.label))
                row.add_widget(icon)
                wrapper.add_widget(row)
        else:
            wrapper.add_widget(MDLabel(text="No download links found.", halign="center", text_color=(1, 0.6, 0.6, 1)))
        self.ids.content.add_widget(wrapper)

    def download_link(self, url: str, label: str, *_args) -> None:
        app = MDApp.get_running_app()
        self.set_status(f"Downloading {label}...")
        app.start_download(url, label)
        app.open_download_screen()

    def show_download_complete(self, message: str) -> None:
        self.clear_content()
        self.set_status(message)
        self.ids.content.add_widget(MDLabel(text=message, halign="center", text_color=(0.76, 1.0, 0.76, 1)))

    def show_error(self, message: str) -> None:
        self.clear_content()
        self.set_status(message)
        self.ids.content.add_widget(MDLabel(text=message, halign="center", text_color=(1, 0.68, 0.68, 1)))


class DownloadScreen(BaseContentScreen):
    def on_pre_enter(self, *args):
        self.render_download_state()

    def render_download_state(self) -> None:
        app = MDApp.get_running_app()
        progress = app.state.download_progress
        self.clear_content()

        header = MDBoxLayout(orientation="horizontal", size_hint_y=None, height=dp(44), spacing=dp(8))
        back_button = MDButton(md_bg_color=(0.17, 0.19, 0.27, 1), size_hint_x=None, width=dp(120))
        back_button.add_widget(MDButtonText(text="Back"))
        back_button.bind(on_release=lambda *_: app.go_back_from_downloads())
        header.add_widget(back_button)
        header.add_widget(MDLabel(text="Live Download", bold=True, halign="center", text_color=(1, 1, 1, 1)))
        header.add_widget(MDLabel(text="", size_hint_x=None, width=dp(120)))

        panel = MDCard(md_bg_color=(0.10, 0.12, 0.16, 1), radius=[dp(18), dp(18), dp(18), dp(18)], padding=dp(16), size_hint_y=None)
        panel.bind(minimum_height=panel.setter("height"))
        content = MDBoxLayout(orientation="vertical", spacing=dp(12), size_hint_y=None)
        content.bind(minimum_height=content.setter("height"))
        content.add_widget(header)
        content.add_widget(MDLabel(text=progress.title or "No active download", bold=True, halign="center", text_color=(1, 1, 1, 1), size_hint_y=None, height=dp(34)))
        content.add_widget(MDLabel(text=progress.status, halign="center", text_color=(0.78, 0.86, 1, 1), size_hint_y=None, height=dp(28)))

        bar = ProgressBar(max=100, value=progress.percent, size_hint_y=None, height=dp(18))
        content.add_widget(bar)
        content.add_widget(MDLabel(text=f"{progress.percent:.1f}%", halign="center", text_color=(1, 0.85, 0.3, 1), size_hint_y=None, height=dp(28)))
        content.add_widget(MDLabel(text=f"Downloaded: {self._format_bytes(progress.downloaded_bytes)}", halign="center", text_color=(0.9, 0.9, 0.9, 1), size_hint_y=None, height=dp(24)))
        content.add_widget(MDLabel(text=f"Total: {self._format_bytes(progress.total_bytes)}", halign="center", text_color=(0.9, 0.9, 0.9, 1), size_hint_y=None, height=dp(24)))
        if progress.file_path:
            content.add_widget(MDLabel(text=f"Saved to: {progress.file_path}", halign="center", text_color=(0.8, 0.9, 1, 1), size_hint_y=None, height=dp(24)))

        panel.add_widget(content)
        self.ids.content.add_widget(panel)

    def update_progress(self, progress: DownloadProgress) -> None:
        app = MDApp.get_running_app()
        app.state.download_progress = progress
        self.render_download_state()

    def show_complete(self, progress: DownloadProgress) -> None:
        self.update_progress(progress)

    def show_error(self, message: str) -> None:
        self.clear_content()
        self.ids.content.add_widget(MDLabel(text=message, halign="center", text_color=(1, 0.68, 0.68, 1)))

    def _format_bytes(self, value: int) -> str:
        if value <= 0:
            return "Unknown"
        units = ["B", "KB", "MB", "GB"]
        size = float(value)
        for unit in units:
            if size < 1024.0 or unit == units[-1]:
                return f"{size:.1f} {unit}"
            size /= 1024.0
