"""Fetcher abstraction used by the recipe runner.

Recipes are executed against a ``Fetcher`` rather than calling
``urllib``/``requests`` directly, so the runner can be exercised in
tests with a deterministic fake instead of hitting real government
endpoints on every test run (or in an environment with no network
egress at all).
"""
from __future__ import annotations

import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Protocol


@dataclass(frozen=True)
class FetchResult:
    status_code: int
    content: bytes
    content_type: str | None
    fetched_at: str


class Fetcher(Protocol):
    def fetch(self, url: str, params: dict) -> FetchResult: ...


class HTTPFetcher:
    """Real network fetcher, stdlib-only (``urllib.request``).

    Not exercised by the automated test suite -- see
    tests/test_runner.py, which uses a fake fetcher instead. This
    implementation is provided so a future mission can run real
    recipes without having to design the fetch layer from scratch.
    """

    def __init__(self, timeout_seconds: float = 30.0, user_agent: str = "publicgraph-usa/0.1"):
        self.timeout_seconds = timeout_seconds
        self.user_agent = user_agent

    def fetch(self, url: str, params: dict) -> FetchResult:
        if params:
            query = urllib.parse.urlencode(params)
            separator = "&" if "?" in url else "?"
            url = f"{url}{separator}{query}"
        request = urllib.request.Request(url, headers={"User-Agent": self.user_agent})
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                content = response.read()
                status_code = response.status
                content_type = response.headers.get("Content-Type")
        except urllib.error.HTTPError as exc:
            content = exc.read()
            status_code = exc.code
            content_type = exc.headers.get("Content-Type") if exc.headers else None
        return FetchResult(
            status_code=status_code,
            content=content,
            content_type=content_type,
            fetched_at=datetime.now(timezone.utc).isoformat(),
        )

