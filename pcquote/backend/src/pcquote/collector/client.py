"""Polite HTTP client for public sources, ported from buildmate (pipeline/http.mjs).

Rules: HTTPS to allowed hosts only; robots.txt honored with Crawl-delay; at least
2 s between requests to one origin; no redirects; 3 attempts with backoff, giving up
when Retry-After exceeds 60 s; 8 MB response limit; a self-identifying User-Agent.
Pages are cached with their ETag / Last-Modified so unchanged pages come back as 304.
"""

from __future__ import annotations

import hashlib
import re
import time
from datetime import datetime, timezone
from threading import Lock
from typing import Protocol
from urllib.parse import unquote, urlsplit

import httpx

from pcquote.collector.parse import SourceError

AGENT = "DrRobot/0.3 (+PC-component-price-monitor; no AI training)"
ROBOT_NAME = "DrRobot"
ALLOWED_HOSTS = {"prod.danawa.com", "search.danawa.com", "openapi.naver.com", "opendata.blender.org"}
RETRY_STATUS = {429, 500, 502, 503, 504}
MAX_BYTES = 8_000_000


def utc_iso(t: datetime | None = None) -> str:
    t = t or datetime.now(timezone.utc)
    return t.astimezone(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


class Robots:
    """robots.txt with the matching rules of the robots-parser package buildmate used.

    Groups are chosen by the most specific matching user-agent (else '*'); `*` and `$`
    wildcards are supported; the longest matching rule wins and Allow wins ties.
    """

    def __init__(self, text: str):
        self.groups: list[tuple[list[str], list[tuple[bool, str]], float | None]] = []
        agents: list[str] = []
        rules: list[tuple[bool, str]] = []
        delay: float | None = None
        in_rules = False
        for raw in text.splitlines():
            line = raw.split("#", 1)[0].strip()
            if ":" not in line:
                continue
            key, value = (s.strip() for s in line.split(":", 1))
            key = key.lower()
            if key == "user-agent":
                if in_rules:
                    self.groups.append((agents, rules, delay))
                    agents, rules, delay, in_rules = [], [], None, False
                agents.append(value.lower())
            elif key in ("allow", "disallow") and agents:
                in_rules = True
                if value or key == "allow":
                    rules.append((key == "allow", value))
            elif key == "crawl-delay" and agents:
                in_rules = True
                try:
                    delay = float(value)
                except ValueError:
                    pass
        if agents:
            self.groups.append((agents, rules, delay))

    def _group(self, agent: str):
        agent = agent.lower()
        best, best_len = None, -1
        for group in self.groups:
            for name in group[0]:
                if name != "*" and agent.startswith(name) and len(name) > best_len:
                    best, best_len = group, len(name)
        if best:
            return best
        return next((g for g in self.groups if "*" in g[0]), None)

    @staticmethod
    def _match(pattern: str, path: str) -> bool:
        regex = "".join(".*" if c == "*" else re.escape(c) for c in pattern.rstrip("$"))
        return re.match(regex + ("$" if pattern.endswith("$") else ""), path) is not None

    def allowed(self, url: str, agent: str = ROBOT_NAME) -> bool:
        group = self._group(agent)
        if not group:
            return True
        u = urlsplit(url)
        path = unquote(u.path or "/") + (f"?{unquote(u.query)}" if u.query else "")
        best: tuple[int, bool] | None = None
        for allow, pattern in group[1]:
            if self._match(unquote(pattern), path):
                rank = (len(pattern), allow)
                if best is None or rank > best:
                    best = rank
        return True if best is None else best[1]

    def crawl_delay(self, agent: str = ROBOT_NAME) -> float | None:
        group = self._group(agent)
        return group[2] if group else None


class PageCache(Protocol):
    def get(self, url: str) -> dict | None: ...
    def put(self, page: dict) -> None: ...


class SourceClient:
    def __init__(self, client: httpx.Client | None = None, min_delay: float = 2.0, sleep=time.sleep,
                 cache: PageCache | None = None, cache_ttl: float = 0):
        self.http = client or httpx.Client(follow_redirects=False, timeout=30)
        self.min_delay = min_delay
        self.sleep = sleep
        self.cache = cache
        self.cache_ttl = cache_ttl
        self.robots: dict[str, Robots] = {}
        self.next_at: dict[str, float] = {}
        self._lock = Lock()

    def raw(self, url: str, headers: dict | None = None, stream: bool = False) -> httpx.Response:
        u = urlsplit(url)
        if u.scheme != "https" or u.hostname not in ALLOWED_HOSTS:
            raise SourceError("허용되지 않은 수집 URL", "invalid_url")
        for attempt in range(3):
            try:
                request = self.http.build_request("GET", url, headers={"User-Agent": AGENT, **(headers or {})})
                r = self.http.send(request, stream=True)
            except httpx.HTTPError as e:
                if attempt == 2:
                    raise SourceError(f"수집 요청 실패: {e}") from e
                self.sleep(2 ** attempt)
                continue
            if r.status_code in RETRY_STATUS and attempt < 2:
                retry = r.headers.get("retry-after")
                r.close()
                wait = float(retry) if retry and retry.isdigit() else 0
                if wait > 60:
                    raise SourceError("Retry-After가 길어 이번 실행을 보류합니다.", "rate_limited")
                self.sleep(wait or 2 ** attempt)
                continue
            if r.status_code >= 300 and r.status_code != 304:
                r.close()
                raise SourceError(f"수집 응답 HTTP {r.status_code}", f"http_{r.status_code}")
            if not stream:
                self._read(r, MAX_BYTES)
            return r
        raise SourceError("수집 재시도 한도 초과")

    @staticmethod
    def _read(r: httpx.Response, limit: int) -> bytes:
        chunks, size = [], 0
        try:
            for chunk in r.iter_bytes():
                size += len(chunk)
                if size > limit:
                    raise SourceError("원문 크기 제한을 초과했습니다.", "too_large")
                chunks.append(chunk)
        finally:
            r.close()
        r._content = b"".join(chunks)
        return r._content

    def _policy(self, origin: str) -> Robots:
        if origin not in self.robots:
            self.robots[origin] = Robots(self.raw(origin + "/robots.txt").text)
        return self.robots[origin]

    def text(self, url: str, *, api: bool = False, headers: dict | None = None, ttl: float | None = None) -> dict:
        """Page as {url, text, fetchedAt, hash, etag, lastModified}. Requests with credentials (api) are never cached."""
        u = urlsplit(url)
        origin = f"{u.scheme}://{u.netloc}"
        ttl = self.cache_ttl if ttl is None else ttl
        cached = self.cache.get(url) if self.cache and not api else None
        if ttl and cached and time.time() - _epoch(cached["fetchedAt"]) < ttl:
            return cached
        with self._lock:
            delay = self.min_delay
            if not api:
                policy = self._policy(origin)
                if not policy.allowed(url):
                    raise SourceError("robots.txt가 이 경로의 수집을 제한합니다.", "robots_denied")
                delay = max(delay, policy.crawl_delay() or 0)
            wait = self.next_at.get(origin, 0) - time.monotonic()
            if wait > 0:
                self.sleep(wait)
            self.next_at[origin] = time.monotonic() + delay
            conditional = {}
            if cached and cached.get("etag"):
                conditional["If-None-Match"] = cached["etag"]
            if cached and cached.get("lastModified"):
                conditional["If-Modified-Since"] = cached["lastModified"]
            r = self.raw(url, {**(headers or {}), **conditional})
        if r.status_code == 304:
            if not cached:
                raise SourceError("캐시 없는 304 응답", "invalid_cache")
            text = cached["text"]
        else:
            text = r.content.decode("utf-8", errors="replace")
        page = {"url": url, "text": text, "fetchedAt": utc_iso(), "hash": hashlib.sha256(text.encode()).hexdigest(),
                "etag": r.headers.get("etag") or (cached or {}).get("etag"),
                "lastModified": r.headers.get("last-modified") or (cached or {}).get("lastModified")}
        if self.cache and not api:
            self.cache.put(page)
        return page


def _epoch(iso: str) -> float:
    return datetime.fromisoformat(iso.replace("Z", "+00:00")).timestamp()
