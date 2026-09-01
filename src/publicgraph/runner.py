"""Executes an acquisition recipe against a Fetcher and records
artifact-level provenance for every step.

This is the "reproducible acquisition recipes" half of the mission: a
recipe plus a runner run should always produce the same request shape,
and every fetched artifact is recorded with enough metadata (source,
recipe, version, URL, checksum, timestamp, HTTP status) to answer "where
did this file come from and can I verify it hasn't changed" later.

Turning a fetched artifact's *contents* into FieldAssertions (parsing,
extraction) is out of scope for this core and is left to future,
source-specific missions -- see docs/ARCHITECTURE.md.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

from publicgraph.fetchers import Fetcher
from publicgraph.recipes import Recipe


class RunnerError(RuntimeError):
    """Raised when a recipe step fails after exhausting its retries."""


@dataclass(frozen=True)
class ArtifactProvenance:
    recipe_id: str
    source_id: str
    recipe_version: int
    step_index: int
    url: str
    output_path: str
    checksum_algorithm: str
    checksum: str
    status_code: int
    content_type: str | None
    fetched_at: str
    attempts: int


def _checksum(algorithm: str, content: bytes) -> str:
    hasher = hashlib.new(algorithm)
    hasher.update(content)
    return hasher.hexdigest()


def run_recipe(
    recipe: Recipe,
    fetcher: Fetcher,
    output_dir: Path,
) -> list[ArtifactProvenance]:
    """Execute every step of ``recipe`` using ``fetcher``, writing
    fetched content under ``output_dir`` and returning one
    ArtifactProvenance record per step.

    Retries a failing step (any non-2xx status) up to
    ``recipe.retry_max_attempts`` times before raising RunnerError; the
    caller decides what "failing" means for their fetcher (a fake used
    in tests can simulate transient failures to exercise this path).
    """
    records: list[ArtifactProvenance] = []
    for index, step in enumerate(recipe.steps):
        last_result = None
        for attempt in range(1, recipe.retry_max_attempts + 1):
            result = fetcher.fetch(step.url, step.params)
            last_result = result
            if 200 <= result.status_code < 300:
                break
        else:
            assert last_result is not None
            raise RunnerError(
                f"recipe {recipe.id!r} step {index} ({step.url}) failed after "
                f"{recipe.retry_max_attempts} attempt(s): HTTP {last_result.status_code}"
            )

        destination = output_dir / step.output_relpath
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(last_result.content)

        records.append(
            ArtifactProvenance(
                recipe_id=recipe.id,
                source_id=recipe.source_id,
                recipe_version=recipe.version,
                step_index=index,
                url=step.url,
                output_path=str(destination),
                checksum_algorithm=recipe.checksum_algorithm,
                checksum=_checksum(recipe.checksum_algorithm, last_result.content),
                status_code=last_result.status_code,
                content_type=last_result.content_type,
                fetched_at=last_result.fetched_at,
                attempts=attempt,
            )
        )
    return records
