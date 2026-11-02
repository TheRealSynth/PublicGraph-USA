"""Unit tests for HTTPFetcher's request construction and response
handling. These are fully mocked -- no real network access -- since the
runner is exercised against a fake Fetcher elsewhere (test_runner.py)
and this repository should not depend on live network egress to pass
its test suite.
"""
import io
import urllib.error
from unittest.mock import MagicMock, patch

from publicgraph.fetchers import HTTPFetcher


class _FakeResponse:
    def __init__(self, body: bytes, status: int, content_type: str):
        self._body = body
        self.status = status
        self.headers = {"Content-Type": content_type}

    def read(self):
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        return False


def test_fetch_success_returns_result_with_content_and_status():
    fetcher = HTTPFetcher()
    fake_response = _FakeResponse(b"hello", 200, "text/plain")
    with patch("urllib.request.urlopen", return_value=fake_response) as urlopen:
        result = fetcher.fetch("https://example.gov/data", {})
    assert result.status_code == 200
    assert result.content == b"hello"
    assert result.content_type == "text/plain"
    request = urlopen.call_args.args[0]
    assert request.full_url == "https://example.gov/data"
    assert request.headers.get("User-agent") == fetcher.user_agent


def test_fetch_encodes_query_params():
    fetcher = HTTPFetcher()
    fake_response = _FakeResponse(b"{}", 200, "application/json")
    with patch("urllib.request.urlopen", return_value=fake_response) as urlopen:
        fetcher.fetch("https://example.gov/data", {"year": "2026", "state": "WA"})
    request = urlopen.call_args.args[0]
    assert request.full_url in (
        "https://example.gov/data?year=2026&state=WA",
        "https://example.gov/data?state=WA&year=2026",
    )


def test_fetch_http_error_is_captured_not_raised():
    fetcher = HTTPFetcher()
    error = urllib.error.HTTPError(
        url="https://example.gov/missing",
        code=404,
        msg="Not Found",
        hdrs={"Content-Type": "text/plain"},
        fp=io.BytesIO(b"not found"),
    )
    with patch("urllib.request.urlopen", side_effect=error):
        result = fetcher.fetch("https://example.gov/missing", {})
    assert result.status_code == 404
    assert result.content == b"not found"
