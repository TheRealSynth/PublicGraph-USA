import json

import pytest

from publicgraph.recipes import (
    DEFAULT_RECIPES_DIR,
    RecipeError,
    load_recipe_file,
    load_recipes,
    validate_recipe_dict,
)
from publicgraph.registry import load_registry

VALID_RECIPE = {
    "id": "example-recipe",
    "source_id": "example-source",
    "version": 1,
    "description": "Fetch the example page.",
    "steps": [
        {
            "type": "http_get",
            "url": "https://example.gov/data.json",
            "output_relpath": "example/data.json",
        }
    ],
    "checksum_algorithm": "sha256",
}


def test_valid_recipe_has_no_errors():
    assert validate_recipe_dict(VALID_RECIPE) == []


def test_recipe_requires_at_least_one_step():
    bad = dict(VALID_RECIPE, steps=[])
    errors = validate_recipe_dict(bad)
    assert any("minItems" in e for e in errors)


def test_recipe_rejects_non_https_step_url():
    bad = json.loads(json.dumps(VALID_RECIPE))
    bad["steps"][0]["url"] = "http://example.gov/data.json"
    errors = validate_recipe_dict(bad)
    assert any("url" in e for e in errors)


def test_recipe_rejects_unknown_checksum_algorithm():
    bad = dict(VALID_RECIPE, checksum_algorithm="md5")
    errors = validate_recipe_dict(bad)
    assert any("checksum_algorithm" in e for e in errors)


def test_default_recipes_load_and_resolve_against_registry():
    registry = load_registry()
    recipes = load_recipes(registry=registry)
    assert "census-acs-homepage-probe" in recipes
    recipe = recipes["census-acs-homepage-probe"]
    assert recipe.source_id == "census-acs"
    assert recipe.source_id in registry


def test_recipe_with_unknown_source_is_rejected(tmp_path):
    path = tmp_path / "orphan.json"
    path.write_text(json.dumps(dict(VALID_RECIPE, id="orphan", source_id="does-not-exist")))
    registry = load_registry()
    with pytest.raises(RecipeError, match="unknown source id"):
        load_recipes(tmp_path, registry=registry)


def test_recipe_without_registry_skips_cross_reference_check(tmp_path):
    path = tmp_path / "orphan.json"
    path.write_text(json.dumps(dict(VALID_RECIPE, id="orphan", source_id="does-not-exist")))
    recipes = load_recipes(tmp_path)
    assert "orphan" in recipes


def test_load_recipe_file_rejects_invalid_json(tmp_path):
    path = tmp_path / "bad.json"
    path.write_text(json.dumps(dict(VALID_RECIPE, version=0)))
    with pytest.raises(RecipeError):
        load_recipe_file(path)


def test_every_bundled_recipe_file_is_valid():
    for path in sorted(DEFAULT_RECIPES_DIR.glob("*.json")):
        load_recipe_file(path)
