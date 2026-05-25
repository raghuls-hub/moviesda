from __future__ import annotations

import mimetypes
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse
from typing import Callable

import requests

from moviesda_app.config import DEFAULT_HEADERS
from moviesda_app.models import DownloadResult


@dataclass
class DownloadService:
    download_dir: Path
    timeout: int = 15

    def __post_init__(self) -> None:
        self.download_dir = self.download_dir.expanduser()
        self.download_dir.mkdir(parents=True, exist_ok=True)
        self.session = requests.Session()
        self.session.headers.update(DEFAULT_HEADERS)
        self.timeout = int(self.timeout)

    def resolve_and_download(
        self,
        url: str,
        referer: str | None = None,
        progress_callback: Callable[[int, int], None] | None = None,
    ) -> DownloadResult:
        headers = {}
        if referer:
            headers["Referer"] = referer
        response = self.session.get(url, headers=headers, timeout=self.timeout, stream=True)
        final_url = response.url
        file_name = self._file_name_from_response(final_url, response.headers.get("content-disposition"))
        file_path = self._unique_path(self.download_dir / file_name)
        total_bytes = int(response.headers.get("content-length") or 0)
        downloaded_bytes = 0
        with file_path.open("wb") as handle:
            for chunk in response.iter_content(chunk_size=1024 * 256):
                if chunk:
                    handle.write(chunk)
                    downloaded_bytes += len(chunk)
                    if progress_callback:
                        progress_callback(downloaded_bytes, total_bytes)
        return DownloadResult(
            source_url=url,
            final_url=final_url,
            file_path=file_path,
            content_type=response.headers.get("content-type", ""),
            size_bytes=file_path.stat().st_size,
        )

    def _file_name_from_response(self, url: str, content_disposition: str | None) -> str:
        if content_disposition and "filename=" in content_disposition:
            name = content_disposition.split("filename=", 1)[1].strip().strip('"\'')
            if name:
                return name
        parsed = urlparse(url)
        name = Path(parsed.path).name
        if name:
            return name
        guessed = mimetypes.guess_extension("application/octet-stream") or ".bin"
        return f"download{guessed}"

    def _unique_path(self, path: Path) -> Path:
        candidate = path
        index = 1
        while candidate.exists():
            candidate = path.with_stem(f"{path.stem}_{index}")
            index += 1
        return candidate
