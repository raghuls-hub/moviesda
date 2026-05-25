from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}


@dataclass(frozen=True)
class AppConfig:
    source_name: str
    base_url: str
    search_query: str
    request_timeout: int
    page_size: int
    download_dir: Path

    @classmethod
    def from_env(cls) -> "AppConfig":
        download_dir = Path(os.environ.get("MOVIESDA_DOWNLOAD_DIR", str(Path.home() / "Downloads")))
        return cls(
            source_name=os.environ.get("MOVIESDA_SOURCE_NAME", "Configured Media Site"),
            base_url=os.environ.get("MOVIESDA_BASE_URL", "").strip(),
            search_query=os.environ.get("MOVIESDA_SEARCH_QUERY", "moviesda").strip(),
            request_timeout=int(os.environ.get("MOVIESDA_REQUEST_TIMEOUT", "15")),
            page_size=int(os.environ.get("MOVIESDA_PAGE_SIZE", "100")),
            download_dir=download_dir,
        )
