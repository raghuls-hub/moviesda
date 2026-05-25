from __future__ import annotations

import re
import urllib.parse
from dataclasses import dataclass

import requests
from bs4 import BeautifulSoup

from moviesda_app.config import DEFAULT_HEADERS
from moviesda_app.models import DownloadOption, MovieCard, MovieDetail, MoviePage, QualityLink, YearOption


MEDIA_EXTENSIONS = (".mp4", ".mkv", ".avi", ".mov")


@dataclass
class SourceService:
    base_url: str = ""
    search_query: str = "moviesda"
    timeout: int = 15

    def __post_init__(self) -> None:
        self.session = requests.Session()
        self.session.headers.update(DEFAULT_HEADERS)
        self.timeout = int(self.timeout)

    def get(self, url: str, *, referer: str | None = None, allow_redirects: bool = True) -> requests.Response:
        headers = {}
        if referer:
            headers["Referer"] = referer
        return self.session.get(url, headers=headers, timeout=self.timeout, allow_redirects=allow_redirects)

    def discover_base_url(self) -> str | None:
        if self.base_url:
            return self.base_url.rstrip("/")
        query = self.search_query.strip() or "moviesda"
        base_url = self.get_moviesda_base_url(query)
        if base_url:
            return base_url
        if query != "moviesda":
            return self.get_moviesda_base_url("moviesda")
        return None

    def get_moviesda_base_url(self, query: str = "moviesda") -> str | None:
        encoded = urllib.parse.quote(query)
        url = f"https://html.duckduckgo.com/html/?q={encoded}"
        r = requests.get(url, headers=DEFAULT_HEADERS, timeout=15)
        soup = BeautifulSoup(r.text, "html.parser")
        for result in soup.select("a.result__url"):
            href = result.get("href", "")
            parsed = urllib.parse.urlparse(href)
            params = urllib.parse.parse_qs(parsed.query)
            actual = urllib.parse.unquote(params.get("uddg", [href])[0])
            if "moviesda" in actual.lower() and actual.startswith("http"):
                # Return just the base (scheme + netloc)
                p = urllib.parse.urlparse(actual)
                return f"{p.scheme}://{p.netloc}"
        return None

    def get_latest_year_link(self, base_url: str) -> str | None:
        response = self.get(base_url)
        soup = BeautifulSoup(response.text, "html.parser")
        year_links: dict[int, str] = {}
        for anchor in soup.find_all("a", href=True):
            text = anchor.get_text(strip=True)
            match = re.search(r"(20\d{2})", text) or re.search(r"(20\d{2})", anchor["href"])
            if match:
                year = int(match.group(1))
                year_links.setdefault(year, urllib.parse.urljoin(base_url, anchor["href"]))
        if not year_links:
            return None
        return year_links[max(year_links)]

    def resolve_to_home_html(self, start_url: str, base_url: str, max_hops: int = 6) -> str | None:
        current_url = start_url
        for _ in range(max_hops):
            if current_url.endswith("home.html"):
                return current_url
            response = self.get(current_url, referer=base_url)
            if response.url.endswith("home.html"):
                return response.url
            soup = BeautifulSoup(response.text, "html.parser")
            next_url = self._find_home_link(soup, response.text)
            if not next_url:
                return None
            current_url = urllib.parse.urljoin(current_url, next_url)
        return None

    def get_year_movie_links(self, home_html_url: str) -> dict[str, dict[str, str]]:
        response = self.get(home_html_url)
        soup = BeautifulSoup(response.text, "html.parser")
        year_links: dict[str, dict[str, str]] = {}
        for div in soup.find_all("div", class_="f"):
            anchor = div.find("a", href=True)
            if not anchor:
                continue
            label = anchor.get_text(strip=True)
            href = anchor["href"]
            match = re.search(r"(20\d{2})", label) or re.search(r"(20\d{2})", href)
            if not match:
                continue
            year = match.group(1)
            year_links[year] = {"label": label or year, "url": urllib.parse.urljoin(home_html_url, href)}
        return year_links

    def get_div_f_links(self, url: str, referer: str | None = None) -> list[dict[str, str]]:
        response = self.get(url, referer=referer)
        soup = BeautifulSoup(response.text, "html.parser")
        links: list[dict[str, str]] = []
        for div in soup.find_all("div", class_="f"):
            anchor = div.find("a", href=True)
            if anchor:
                links.append({"label": anchor.get_text(strip=True), "url": urllib.parse.urljoin(url, anchor["href"])})
        return links

    def get_coral_link(self, resolution_url: str, referer: str | None = None) -> dict[str, str] | None:
        response = self.get(resolution_url, referer=referer)
        soup = BeautifulSoup(response.text, "html.parser")
        folder = soup.find("div", class_="folder")
        if folder:
            anchor = folder.find("a", class_="coral", href=True)
            if anchor:
                return {"label": anchor.get_text(strip=True), "url": urllib.parse.urljoin(resolution_url, anchor["href"])}
        anchor = soup.find("a", class_="coral", href=True)
        if anchor:
            return {"label": anchor.get_text(strip=True), "url": urllib.parse.urljoin(resolution_url, anchor["href"])}
        return None

    def get_moviespage_link(self, download_page_url: str, referer: str | None = None) -> dict[str, str] | None:
        response = self.get(download_page_url, referer=referer)
        soup = BeautifulSoup(response.text, "html.parser")
        download_div = soup.find("div", class_="download")
        if download_div:
            dlink = download_div.find("div", class_="dlink")
            if dlink:
                anchor = dlink.find("a", href=True)
                if anchor:
                    return {"label": anchor.get_text(strip=True), "url": anchor["href"]}
        dlink = soup.find("div", class_="dlink")
        if dlink:
            anchor = dlink.find("a", href=True)
            if anchor:
                return {"label": anchor.get_text(strip=True), "url": anchor["href"]}
        return None

    def follow_until_mp4(self, start_url: str, referer: str | None = None, max_hops: int = 10) -> dict[str, object]:
        current_url = start_url
        current_referer = referer or self.base_url or start_url
        metadata: dict[str, str] = {}
        for hop in range(max_hops):
            response = self.get(current_url, referer=current_referer)
            soup = BeautifulSoup(response.text, "html.parser")
            if hop == 0:
                metadata.update(self._extract_metadata(soup))
            server_links = [
                {"label": anchor.get_text(strip=True), "url": anchor["href"]}
                for anchor in soup.find_all("a", href=True)
                if "download server" in anchor.get_text(strip=True).lower()
            ]
            if not server_links:
                return {"meta": metadata, "download_links": self._find_direct_media_links(soup, current_url)}
            final = [link for link in server_links if self._is_media_link(link["url"])]
            if final:
                return {"meta": metadata, "download_links": final}
            current_referer = current_url
            current_url = server_links[0]["url"]
        return {"meta": metadata, "download_links": []}

    def crawl_movie(self, movie_url: str, base_url: str) -> list[dict[str, object]]:
        all_results: list[dict[str, object]] = []
        level1 = self.get_div_f_links(movie_url, base_url)
        for group in level1:
            level2 = self.get_div_f_links(group["url"], movie_url)
            for resolution in level2:
                coral = self.get_coral_link(resolution["url"], group["url"])
                if not coral:
                    continue
                moviespage = self.get_moviespage_link(coral["url"], resolution["url"])
                if not moviespage:
                    continue
                result = self.follow_until_mp4(moviespage["url"], coral["url"])
                if result["download_links"]:
                    all_results.append(
                        {
                            "group": group["label"],
                            "resolution": resolution["label"],
                            "meta": result["meta"],
                            "links": result["download_links"],
                        }
                    )
        return all_results

    def get_movie_detail(self, movie_url: str, base_url: str) -> MovieDetail:
        response = self.get(movie_url, referer=base_url)
        soup = BeautifulSoup(response.text, "html.parser")
        title, metadata = self._extract_movie_title_and_metadata(soup, movie_url)
        poster_url = self._extract_poster_url(soup, movie_url)
        synopsis = self._extract_synopsis(soup)
        links = [QualityLink(label=item.label, url=item.url) for item in self._extract_quality_links(soup, movie_url, base_url)]
        if not links:
            for result in self.crawl_movie(movie_url, base_url):
                for link in result["links"]:
                    links.append(QualityLink(label=link["label"], url=link["url"]))
        return MovieDetail(title=title, url=movie_url, poster_url=poster_url, synopsis=synopsis, metadata=metadata, links=links)

    def list_movies(self, year_url: str, page_index: int = 0, page_size: int = 100) -> MoviePage:
        requested_page = max(page_index + 1, 1)
        page_url = self._build_page_url(year_url, requested_page)
        response = self.get(page_url)
        soup = BeautifulSoup(response.text, "html.parser")
        cards = self._extract_movie_cards(soup, response.url)
        current_page, total_pages, page_numbers = self._extract_pagination(soup, response.url)
        if not page_numbers:
            page_numbers = list(range(1, total_pages + 1))
        return MoviePage(
            movies=cards,
            current_page=current_page,
            total_pages=total_pages,
            page_numbers=page_numbers,
        )

    def _extract_movie_cards(self, soup: BeautifulSoup, page_url: str) -> list[MovieCard]:
        listing_html = self._extract_listing_html(soup)
        scope = BeautifulSoup(listing_html, "html.parser")
        cards: list[MovieCard] = []
        for container in scope.find_all("div", class_="f"):
            anchor = container.find("a", href=True)
            if not anchor:
                continue
            title = anchor.get_text(" ", strip=True)
            image = container.find("img", src=True)
            if not title:
                continue
            poster = ""
            if image and image.get("src"):
                img_src = image["src"]
                if "folder.svg" not in img_src.lower():
                    poster = urllib.parse.urljoin(page_url, img_src)
            href = urllib.parse.urljoin(page_url, anchor["href"])
            cards.append(MovieCard(title=title, url=href, poster_url=poster, summary=""))
        unique_cards: list[MovieCard] = []
        seen_urls: set[str] = set()
        for card in cards:
            if card.url in seen_urls:
                continue
            seen_urls.add(card.url)
            unique_cards.append(card)
        return unique_cards

    def _extract_listing_html(self, soup: BeautifulSoup) -> str:
        root = soup.find("main") or soup
        root_html = str(root)

        start_match = re.search(r'<div\s+class="line"[^>]*>\s*[^<]*20\d{2}[^<]*movies\s*</div>', root_html, re.I)
        end_match = re.search(r'<div\s+class="line"[^>]*>\s*A-Z\s+Movie\s+Categories\s*</div>', root_html, re.I)

        start_idx = start_match.end() if start_match else 0
        end_idx = end_match.start() if end_match else len(root_html)
        if end_idx <= start_idx:
            return root_html
        return root_html[start_idx:end_idx]

    def _build_page_url(self, year_url: str, page_number: int) -> str:
        base, _, query = year_url.partition("?")
        params = urllib.parse.parse_qs(query, keep_blank_values=True)
        if page_number <= 1:
            params.pop("page", None)
        else:
            params["page"] = [str(page_number)]
        encoded = urllib.parse.urlencode(params, doseq=True)
        return f"{base}?{encoded}" if encoded else base

    def _extract_pagination(self, soup: BeautifulSoup, page_url: str) -> tuple[int, int, list[int]]:
        current_page = 1
        total_pages = 1
        page_numbers: set[int] = {1}

        parsed = urllib.parse.urlparse(page_url)
        query_page = urllib.parse.parse_qs(parsed.query).get("page", [None])[0]
        if query_page and str(query_page).isdigit():
            current_page = int(str(query_page))

        current_tag = soup.select_one("#currentPage")
        if current_tag:
            text = current_tag.get_text(strip=True)
            if text.isdigit():
                current_page = int(text)

        total_tag = soup.select_one("#totalPages")
        if total_tag:
            text = total_tag.get_text(strip=True)
            if text.isdigit():
                total_pages = int(text)

        for anchor in soup.select("ul.pagination a[href]"):
            href = anchor.get("href", "")
            if not href:
                continue
            full = urllib.parse.urljoin(page_url, href)
            parsed_href = urllib.parse.urlparse(full)
            page = urllib.parse.parse_qs(parsed_href.query).get("page", [None])[0]
            if page and str(page).isdigit():
                page_numbers.add(int(str(page)))
            elif parsed_href.path.rstrip("/") == parsed.path.rstrip("/"):
                page_numbers.add(1)

        if page_numbers:
            total_pages = max(total_pages, max(page_numbers), current_page)
        else:
            total_pages = max(total_pages, current_page)
            page_numbers = set(range(1, total_pages + 1))

        return current_page, total_pages, sorted(page_numbers)

    def _extract_quality_links(self, soup: BeautifulSoup, movie_url: str, base_url: str) -> list[DownloadOption]:
        links: list[DownloadOption] = []
        seen_labels: set[str] = set()

        for result in soup.select("#movie-info"):
            for section in result.select(".quality-links a[href], a[href]"):
                label = section.get_text(" ", strip=True)
                href = urllib.parse.urljoin(base_url, section.get("href", ""))
                if not label or not href:
                    continue
                quality_label = self._normalize_quality_label(label)
                if quality_label in seen_labels:
                    continue
                if self._is_media_link(href) or "download" in label.lower() or "server" in label.lower():
                    links.append(DownloadOption(label=quality_label, url=href))
                    seen_labels.add(quality_label)

        if links:
            return links

        fallback: list[DownloadOption] = []
        for result in self.crawl_movie(movie_url, base_url):
            quality_label = f'{result["group"]} • {result["resolution"]}'.strip(" •")
            first_link = next(iter(result["links"]), None)
            if first_link:
                fallback.append(DownloadOption(label=quality_label, url=first_link["url"]))
        return fallback

    def _extract_movie_title_and_metadata(self, soup: BeautifulSoup, fallback: str) -> tuple[str, dict[str, str]]:
        metadata: dict[str, str] = {}
        title = ""

        for li in soup.select("#movie-info ul.movie-info li"):
            strong = li.find("strong")
            span = li.find("span")
            if not strong or not span:
                continue
            key = strong.get_text(" ", strip=True).rstrip(":")
            value = span.get_text(" ", strip=True)
            if key == "Movie":
                title = value
                metadata["Movie"] = value
            elif key in {"Director", "Starring", "Language"}:
                metadata[key] = value

        if not title:
            for node in (soup.find("h1"), soup.find("h2"), soup.find("title")):
                if node:
                    text = node.get_text(strip=True)
                    if text:
                        title = text
                        break

        if not title:
            title = fallback.rsplit("/", 1)[-1]
        return title, metadata

    def _normalize_quality_label(self, label: str) -> str:
        cleaned = re.sub(r"\s+", " ", label).strip()
        cleaned = cleaned.replace("Download Server", "").strip(" -•|")
        return cleaned or "Download"

    def _extract_poster_url(self, soup: BeautifulSoup, base_url: str) -> str:
        image = soup.select_one("#movie-info > div.movie-info-container > picture > img")
        if image and image.get("src"):
            return urllib.parse.urljoin(base_url, image["src"])
        image = soup.find("img", src=True)
        if image:
            return urllib.parse.urljoin(base_url, image["src"])
        meta = soup.find("meta", attrs={"property": "og:image"})
        if meta and meta.get("content"):
            return urllib.parse.urljoin(base_url, meta["content"])
        return ""

    def _extract_synopsis(self, soup: BeautifulSoup) -> str:
        for node in (soup.find("div", class_="synopsis"), soup.find("div", class_="details"), soup.find("p")):
            if node:
                text = node.get_text(" ", strip=True)
                if text:
                    return text[:1000]
        return ""

    def _extract_metadata(self, soup: BeautifulSoup) -> dict[str, str]:
        metadata: dict[str, str] = {}
        for detail in soup.find_all("div", class_="details"):
            text = detail.get_text(" ", strip=True)
            for key in ("File Name", "File Size", "Format", "Duration", "Video Size"):
                if key in text:
                    metadata[key] = text.replace(f"{key}:", "").strip()
        return metadata

    def _find_direct_media_links(self, soup: BeautifulSoup, base_url: str) -> list[dict[str, str]]:
        links: list[dict[str, str]] = []
        for anchor in soup.find_all("a", href=True):
            href = urllib.parse.urljoin(base_url, anchor["href"])
            if self._is_media_link(href):
                links.append({"label": anchor.get_text(strip=True) or "Download", "url": href})
        return links

    def _is_media_link(self, url: str) -> bool:
        lower = url.lower()
        return lower.endswith(MEDIA_EXTENSIONS) or bool(re.search(r"\.(mp4|mkv|avi|mov)(\?.*)?$", lower, re.I))

    def _find_home_link(self, soup: BeautifulSoup, raw_html: str) -> str | None:
        for anchor in soup.find_all("a", href=True):
            if anchor["href"].endswith("home.html"):
                return anchor["href"]
        meta = soup.find("meta", attrs={"http-equiv": re.compile("refresh", re.I)})
        if meta and meta.get("content"):
            match = re.search(r"url=(.+)", meta["content"], re.I)
            if match and "home.html" in match.group(1):
                return match.group(1).strip().strip("'\"")
        for script in soup.find_all("script"):
            if script.string and "home.html" in script.string:
                match = re.search(r'(?:window\.location|location\.href)\s*=\s*["\'](.+?)["\']', script.string)
                if match:
                    return match.group(1)
        matches = re.findall(r'https?://[^\s"\'<>]+home\.html', raw_html)
        if matches:
            return matches[0]
        return None
