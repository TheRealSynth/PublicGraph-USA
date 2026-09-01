import json

import pytest

from publicgraph.registry import (
    DEFAULT_SOURCES_DIR,
    RegistryError,
    load_registry,
    load_source_file,
    validate_source_dict,
)

VALID_SOURCE = {
    "id": "example-source",
    "name": "Example Source",
    "agency": "Example Agency",
    "homepage_url": "https://example.gov",
    "license": "U.S. Government Work",
    "access_method": "http_api",
    "formats": ["json"],
    "update_cadence": "monthly",
    "added_at": "2026-09-01",
}


def test_valid_source_has_no_errors():
    assert validate_source_dict(VALID_SOURCE) == []


def test_missing_required_field_is_rejected():
    bad = dict(VALID_SOURCE)
    del bad["license"]
    errors = validate_source_dict(bad)
    assert any("license" in e for e in errors)


def test_bad_access_method_is_rejected():
    bad = dict(VALID_SOURCE, access_method="carrier_pigeon")
    errors = validate_source_dict(bad)
    assert any("is not one of" in e for e in errors)


def test_bad_url_scheme_is_rejected():
    bad = dict(VALID_SOURCE, homepage_url="http://example.gov")
    errors = validate_source_dict(bad)
    assert any("homepage_url" in e for e in errors)


def test_default_registry_loads_real_example_data():
    registry = load_registry()
    assert len(registry) >= 2
    assert "census-acs" in registry
    assert "bls-cpi" in registry
    source = registry.get("census-acs")
    assert source.agency == "U.S. Census Bureau"


def test_unknown_source_raises():
    registry = load_registry()
    with pytest.raises(RegistryError):
        registry.get("does-not-exist")


def test_load_source_file_rejects_invalid_json(tmp_path):
    bad = dict(VALID_SOURCE, access_method="bogus")
    path = tmp_path / "example-source.json"
    path.write_text(json.dumps(bad))
    with pytest.raises(RegistryError):
        load_source_file(path)


def test_registry_rejects_duplicate_ids(tmp_path):
    (tmp_path / "a.json").write_text(json.dumps(VALID_SOURCE))
    (tmp_path / "b.json").write_text(json.dumps(VALID_SOURCE))
    with pytest.raises(RegistryError, match="duplicate source id"):
        load_registry(tmp_path)


def test_every_bundled_source_file_is_valid_and_self_consistent():
    for path in sorted(DEFAULT_SOURCES_DIR.glob("*.json")):
        source = load_source_file(path)
        assert source.id == path.stem, "convention: filename should match id"
