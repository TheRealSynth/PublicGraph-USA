import hashlib

import pytest

from publicgraph.fetchers import FetchResult
from publicgraph.recipes import Recipe, RecipeStep
from publicgraph.runner import RunnerError, run_recipe

RECIPE = Recipe(
    id="demo-recipe",
    source_id="demo-source",
    version=1,
    description="demo",
    steps=(
        RecipeStep(type="http_get", url="https://example.gov/a.json", output_relpath="a.json"),
        RecipeStep(type="http_get", url="https://example.gov/b.json", output_relpath="sub/b.json"),
    ),
    checksum_algorithm="sha256",
    retry_max_attempts=3,
)


class FakeFetcher:
    def __init__(self, responses):
        # responses: dict[url] -> list of FetchResult, consumed in order
        self._responses = {url: list(results) for url, results in responses.items()}
        self.calls = []

    def fetch(self, url, params):
        self.calls.append((url, params))
        queue = self._responses[url]
        if len(queue) > 1:
            return queue.pop(0)
        return queue[0]


def _ok(content: bytes) -> FetchResult:
    return FetchResult(
        status_code=200, content=content, content_type="application/json", fetched_at="t"
    )


def _fail(status_code: int) -> FetchResult:
    return FetchResult(status_code=status_code, content=b"", content_type=None, fetched_at="t")


def test_run_recipe_writes_files_and_records_provenance(tmp_path):
    fetcher = FakeFetcher(
        {
            "https://example.gov/a.json": [_ok(b'{"a": 1}')],
            "https://example.gov/b.json": [_ok(b'{"b": 2}')],
        }
    )
    records = run_recipe(RECIPE, fetcher, tmp_path)

    assert (tmp_path / "a.json").read_bytes() == b'{"a": 1}'
    assert (tmp_path / "sub" / "b.json").read_bytes() == b'{"b": 2}'

    assert len(records) == 2
    first = records[0]
    assert first.recipe_id == "demo-recipe"
    assert first.source_id == "demo-source"
    assert first.status_code == 200
    assert first.attempts == 1
    assert first.checksum == hashlib.sha256(b'{"a": 1}').hexdigest()


def test_run_recipe_retries_transient_failures(tmp_path):
    fetcher = FakeFetcher(
        {
            "https://example.gov/a.json": [_fail(503), _fail(503), _ok(b"ok")],
            "https://example.gov/b.json": [_ok(b"ok")],
        }
    )
    records = run_recipe(RECIPE, fetcher, tmp_path)
    assert records[0].attempts == 3
    assert records[0].status_code == 200


def test_run_recipe_raises_after_exhausting_retries(tmp_path):
    fetcher = FakeFetcher(
        {
            "https://example.gov/a.json": [_fail(500), _fail(500), _fail(500)],
            "https://example.gov/b.json": [_ok(b"unused")],
        }
    )
    with pytest.raises(RunnerError, match="failed after 3 attempt"):
        run_recipe(RECIPE, fetcher, tmp_path)


def test_run_recipe_stops_at_first_failing_step(tmp_path):
    fetcher = FakeFetcher(
        {
            "https://example.gov/a.json": [_fail(500), _fail(500), _fail(500)],
        }
    )
    with pytest.raises(RunnerError):
        run_recipe(RECIPE, fetcher, tmp_path)
    # step b's url was never called because step a exhausted its retries first
    called_urls = {url for url, _ in fetcher.calls}
    assert "https://example.gov/b.json" not in called_urls
