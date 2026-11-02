from publicgraph.validation import validate

SCHEMA = {
    "type": "object",
    "required": ["id", "count"],
    "additionalProperties": False,
    "properties": {
        "id": {"type": "string", "pattern": r"^[a-z-]+$", "minLength": 2},
        "count": {"type": "integer", "minimum": 0, "maximum": 10},
        "tags": {"type": "array", "items": {"type": "string"}, "minItems": 1},
        "kind": {"type": "string", "enum": ["a", "b"]},
    },
}


def test_valid_instance_has_no_errors():
    assert validate({"id": "abc", "count": 3}, SCHEMA) == []


def test_missing_required_field():
    errors = validate({"count": 3}, SCHEMA)
    assert any("missing required property 'id'" in e for e in errors)


def test_wrong_type():
    errors = validate({"id": "abc", "count": "three"}, SCHEMA)
    assert any("expected integer" in e for e in errors)


def test_bool_is_not_accepted_as_integer():
    errors = validate({"id": "abc", "count": True}, SCHEMA)
    assert any("expected integer, got boolean" in e for e in errors)


def test_pattern_mismatch():
    errors = validate({"id": "ABC", "count": 1}, SCHEMA)
    assert any("does not match pattern" in e for e in errors)


def test_min_length():
    errors = validate({"id": "a", "count": 1}, SCHEMA)
    assert any("minLength" in e for e in errors)


def test_numeric_bounds():
    errors = validate({"id": "ab", "count": 11}, SCHEMA)
    assert any("> maximum" in e for e in errors)


def test_enum_violation():
    errors = validate({"id": "ab", "count": 1, "kind": "z"}, SCHEMA)
    assert any("is not one of" in e for e in errors)


def test_additional_properties_rejected():
    errors = validate({"id": "ab", "count": 1, "surprise": True}, SCHEMA)
    assert any("unexpected property 'surprise'" in e for e in errors)


def test_array_items_validated():
    errors = validate({"id": "ab", "count": 1, "tags": [1, "ok"]}, SCHEMA)
    assert any("tags[0]" in e and "expected string" in e for e in errors)


def test_array_min_items():
    errors = validate({"id": "ab", "count": 1, "tags": []}, SCHEMA)
    assert any("minItems" in e for e in errors)


def test_date_format():
    date_schema = {"type": "string", "format": "date"}
    assert validate("2026-09-01", date_schema) == []
    assert validate("09/01/2026", date_schema) != []


def test_date_time_format():
    dt_schema = {"type": "string", "format": "date-time"}
    assert validate("2026-09-01T00:00:00+00:00", dt_schema) == []
    assert validate("not-a-timestamp", dt_schema) != []
