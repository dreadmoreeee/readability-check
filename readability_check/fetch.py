"""Polite page loading: robots.txt (RFC 9309), GET only, spaced requests."""
from __future__ import annotations

import re
import time
import urllib.error
import urllib.request
from urllib.parse import urlsplit

from . import USER_AGENT
from .rfc9309 import RobotsTxt, fetch as fetch_robots

MAX_PAGE_BYTES = 5 * 1024 * 1024


class FetchError(Exception):
    pass


def decode(data: bytes, header_charset: str | None = None) -> str:
    charset = header_charset
    if not charset:
        m = re.search(rb"<meta[^>]+charset=[\"']?([\w-]+)", data[:4096], re.I)
        charset = m.group(1).decode("ascii", "ignore") if m else "utf-8"
    try:
        return data.decode(charset, "replace")
    except LookupError:
        return data.decode("utf-8", "replace")


def read_file(path: str) -> str:
    try:
        with open(path, "rb") as fh:
            return decode(fh.read(MAX_PAGE_BYTES))
    except OSError as e:
        raise FetchError(f"cannot read {path}: {e.strerror or e}") from e


class Fetcher:
    def __init__(self, delay: float = 1.0, timeout: float = 15.0, use_robots: bool = True):
        self.delay = delay
        self.timeout = timeout
        self.use_robots = use_robots
        self._robots: dict[str, RobotsTxt] = {}
        self._last = 0.0
        self.requests = 0

    def _wait(self, delay: float) -> None:
        remaining = self._last + delay - time.monotonic()
        if self._last and remaining > 0:
            time.sleep(remaining)

    def _touch(self) -> None:
        self._last = time.monotonic()
        self.requests += 1

    def get(self, url: str) -> str:
        parts = urlsplit(url)
        if parts.scheme not in ("http", "https") or not parts.netloc:
            raise FetchError(f"not an http(s) URL: {url}")
        delay = self.delay
        if self.use_robots:
            origin = f"{parts.scheme}://{parts.netloc}"
            if origin not in self._robots:
                self._wait(self.delay)
                self._robots[origin] = fetch_robots(origin, user_agent=USER_AGENT)
                self._touch()
            rules = self._robots[origin]
            if not rules.can_fetch(USER_AGENT, url):
                raise FetchError("blocked by robots.txt")
            cd = rules.crawl_delay(USER_AGENT)
            if cd:
                delay = max(delay, min(cd, 30.0))
        self._wait(delay)
        req = urllib.request.Request(url, headers={
            "User-Agent": USER_AGENT, "Accept": "text/html,application/xhtml+xml"})
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                ctype = resp.headers.get_content_type()
                charset = resp.headers.get_content_charset()
                data = resp.read(MAX_PAGE_BYTES)
        except urllib.error.HTTPError as e:
            raise FetchError(f"HTTP {e.code}") from e
        except (urllib.error.URLError, OSError, ValueError) as e:
            raise FetchError(f"request failed: {getattr(e, 'reason', e)}") from e
        finally:
            self._touch()
        if ctype not in ("text/html", "application/xhtml+xml"):
            raise FetchError(f"not HTML ({ctype})")
        return decode(data, charset)
