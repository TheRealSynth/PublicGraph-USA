"""Acquisition recipes: declarative, versioned descriptions of how to
fetch raw data from a registered source.

A recipe never contains ad-hoc scraping/download logic; it lists steps
(currently just ``http_get``) that a generic runner (runner.py) can
execute against any Fetcher implementation. That keeps recipes
reviewable, diffable, and reproducible: rerunning the same recipe
version against the same source should produce the same request shape
every time.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from publicgraph.registry import Registry, RegistryError
from publicgraph.schemas import RECIPE_SCHEMA
from publicgraph.validation import validate

DEFAULT_RECIPES_DIR = Path(__file__).parent / "data" / "recipes"


class RecipeError(ValueError):
    """Raised for invalid or inconsistent recipe data."""


@dataclass(frozen=True)
class RecipeStep:
    type: str
    url: str
    output_relpath: str
    params: dict = field(default_factory=dict)
    expected_content_type: str | None = None

    @classmethod
    def from_dict(cls, data: dict) -> "RecipeStep":
        return cls(
            type=data["type"],
            url=data["url"],
            output_relpath=data["output_relpath"],
            params=dict(data.get("params", {})),
            expected_content_type=data.get("expected_content_type"),
        )


@dataclass(frozen=True)
class Recipe:
    id: str
    source_id: str
    version: int
    description: str
    steps: tuple[RecipeStep, ...]
    checksum_algorithm: str
    retry_max_attempts: int = 3
    notes: str | None = None

    @classmethod
    def from_dict(cls, data: dict) -> "Recipe":
        return cls(
            id=data["id"],
            source_id=data["source_id"],
            version=data["version"],
            description=data["description"],
            steps=tuple(RecipeStep.from_dict(s) for s in data["steps"]),
            checksum_algorithm=data["checksum_algorithm"],
            retry_max_attempts=data.get("retry_max_attempts", 3),
            notes=data.get("notes"),
        )


def validate_recipe_dict(data: dict) -> list[str]:
    return validate(data, RECIPE_SCHEMA)


def load_recipe_file(path: Path) -> Recipe:
    data = json.loads(path.read_text())
    errors = validate_recipe_dict(data)
    if errors:
        raise RecipeError(f"{path}: " + "; ".join(errors))
    return Recipe.from_dict(data)


def load_recipes(
    recipes_dir: Path = DEFAULT_RECIPES_DIR,
    registry: Registry | None = None,
) -> dict[str, Recipe]:
    """Load and validate every ``*.json`` recipe file in ``recipes_dir``.

    When ``registry`` is given, each recipe's ``source_id`` is checked
    against it -- a recipe that references a source not present in the
    registry is a data-integrity error, not a warning, because a
    dangling reference means the recipe's provenance can never be
    resolved back to a real source.
    """
    recipes: dict[str, Recipe] = {}
    for path in sorted(recipes_dir.glob("*.json")):
        recipe = load_recipe_file(path)
        if recipe.id in recipes:
            raise RecipeError(f"duplicate recipe id {recipe.id!r} in {path}")
        if registry is not None:
            try:
                registry.get(recipe.source_id)
            except RegistryError as exc:
                raise RecipeError(f"{path}: {exc}") from exc
        recipes[recipe.id] = recipe
    return recipes
