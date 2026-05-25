from __future__ import annotations

from dataclasses import dataclass, field

from moviesda_app.models import MovieCard, MovieDetail, YearOption, DownloadJob


@dataclass
class AppState:
    base_url: str = ""
    home_html_url: str = ""
    selected_year: YearOption | None = None
    years: list[YearOption] = field(default_factory=list)
    movies: list[MovieCard] = field(default_factory=list)
    total_site_pages: int = 1
    current_site_page: int = 1
    available_pages: list[int] = field(default_factory=list)
    movie_detail: MovieDetail | None = None
    download_jobs: list[DownloadJob] = field(default_factory=list)
    last_screen: str = "years"
    current_page: int = 0
    status_message: str = ""
