import json

import pytest

from publicgraph.provenance import (
    DEFAULT_ASSERTIONS_DIR,
    FieldAssertion,
    ProvenanceError,
    confidence_band,
    find_conflicts,
    load_assertion_file,
    load_assertions,
    validate_assertion_dict,
)
from publicgraph.registry import load_registry

VALID_ASSERTION = {
    "entity_id": "entity:1",
    "field_name": "some_field",
    "value": 42,
    "source_id": "example-source",
    "method": "manual_entry",
    "confidence": 0.7,
    "observed_at": "2026-09-01T00:00:00+00:00",
}


def test_valid_assertion_has_no_errors():
    assert validate_assertion_dict(VALID_ASSERTION) == []


def test_confidence_out_of_range_is_rejected():
    bad = dict(VALID_ASSERTION, confidence=1.5)
    errors = validate_assertion_dict(bad)
    assert any("confidence" in e for e in errors)


def test_bad_method_is_rejected():
    bad = dict(VALID_ASSERTION, method="guessed")
    errors = validate_assertion_dict(bad)
    assert any("is not one of" in e for e in errors)


@pytest.mark.parametrize(
    "confidence,expected",
    [(1.0, "high"), (0.85, "high"), (0.6, "medium"), (0.5, "medium"), (0.2, "low"), (0.0, "low")],
)
def test_confidence_band(confidence, expected):
    assert confidence_band(confidence) == expected


def test_confidence_band_rejects_out_of_range():
    with pytest.raises(ValueError):
        confidence_band(1.1)


def test_field_assertion_band_property():
    assertion = FieldAssertion.from_dict(VALID_ASSERTION)
    assert assertion.band == "medium"


def test_default_assertions_load_and_resolve_against_registry():
    registry = load_registry()
    assertions = load_assertions(registry=registry)
    assert len(assertions) >= 2
    for assertion in assertions:
        assert assertion.source_id in registry


def test_assertion_with_unknown_source_is_rejected(tmp_path):
    path = tmp_path / "orphan.json"
    path.write_text(json.dumps(dict(VALID_ASSERTION, source_id="does-not-exist")))
    registry = load_registry()
    with pytest.raises(ProvenanceError, match="unknown source id"):
        load_assertion_file(path, registry=registry)


def test_bundled_example_assertions_conflict_by_design():
    assertions = load_assertions()
    conflicts = find_conflicts(assertions)
    key = ("example-entity:demo-state", "population_estimate")
    assert key in conflicts
    assert len(conflicts[key]) == 2
    values = {a.value for a in conflicts[key]}
    assert values == {1000000, 1050000}


def test_find_conflicts_ignores_agreeing_assertions():
    a = FieldAssertion.from_dict(VALID_ASSERTION)
    b = FieldAssertion.from_dict(dict(VALID_ASSERTION, observed_at="2026-09-02T00:00:00+00:00"))
    assert find_conflicts([a, b]) == {}


def test_every_bundled_assertion_file_is_valid():
    for path in sorted(DEFAULT_ASSERTIONS_DIR.glob("*.json")):
        load_assertion_file(path)
