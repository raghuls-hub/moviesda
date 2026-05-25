from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class YearOption:
    year: int
    label: str
    url: str


@dataclass(frozen=True)
class MovieCard:
    title: str
    url: str
    poster_url: str = ""
    summary: str = ""
    year: str = ""


@dataclass(frozen=True)
class MoviePage:
    movies: list[MovieCard] = field(default_factory=list)
    current_page: int = 1
    total_pages: int = 1
    page_numbers: list[int] = field(default_factory=list)


@dataclass(frozen=True)
class DownloadOption:
    label: str
    url: str


@dataclass(frozen=True)
class DownloadProgress:
    title: str = ""
    url: str = ""
    status: str = "Idle"
    percent: float = 0.0
    downloaded_bytes: int = 0
    total_bytes: int = 0
    file_path: str = ""
    completed: bool = False


class JobStatus:
    PENDING = "pending"
    DOWNLOADING = "downloading"
    DONE = "done"
    CANCELLED = "cancelled"
    ERROR = "error"


@dataclass
class DownloadJob:
    id: str
    title: str
    url: str
    referer: str = ""
    status: str = JobStatus.PENDING
    percent: float = 0.0
    downloaded_bytes: int = 0
    total_bytes: int = 0
    file_path: str = ""
    error: str = ""


@dataclass(frozen=True)
class QualityLink:
    label: str
    url: str
    kind: str = "server"
    file_size_bytes: int = 0


@dataclass(frozen=True)
class MovieDetail:
    title: str
    url: str
    poster_url: str = ""
    synopsis: str = ""
    metadata: dict[str, str] = field(default_factory=dict)
    links: list[QualityLink] = field(default_factory=list)


@dataclass(frozen=True)
class DownloadResult:
    source_url: str
    final_url: str
    file_path: Path
    content_type: str = ""
    size_bytes: int = 0
