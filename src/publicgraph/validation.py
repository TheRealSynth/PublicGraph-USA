"""A minimal, dependency-free structural validator.

Supports the small subset of JSON Schema-like features the registry,
recipe, and provenance schemas in this package actually need: type
checking, required fields, enum membership, regex patterns, numeric
bounds, array item validation, and a couple of string formats. This is
not a general JSON Schema implementation; it exists so the core has zero
third-party dependencies (see package docstring in __init__.py).
"""
from __future__ import annotations

import re
from datetime import datetime
from typing import Any

_TYPE_MAP = {
    "string": str,
    "integer": int,
    "number": (int, float),
    "boolean": bool,
    "array": list,
    "object": dict,
}

_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _check_format(value: str, fmt: str, path: str, errors: list[str]) -> None:
    if fmt == "date":
        if not _DATE_RE.match(value):
            errors.append(f"{path}: '{value}' is not a valid YYYY-MM-DD date")
        return
    if fmt == "date-time":
        try:
            datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            errors.append(f"{path}: '{value}' is not a valid ISO-8601 date-time")
        return
    raise ValueError(f"unsupported format: {fmt}")


def validate(instance: Any, schema: dict, path: str = "$") -> list[str]:
    """Validate ``instance`` against ``schema``, returning a list of
    human-readable error strings (empty list means valid)."""
    errors: list[str] = []
    _validate_node(instance, schema, path, errors)
    return errors


def _validate_node(instance: Any, schema: dict, path: str, errors: list[str]) -> None:
    schema_type = schema.get("type")
    if schema_type is not None:
        expected = _TYPE_MAP[schema_type]
        # bool is a subclass of int in Python; only accept it where asked.
        if schema_type != "boolean" and isinstance(instance, bool):
            errors.append(f"{path}: expected {schema_type}, got boolean")
            return
        if not isinstance(instance, expected):
            errors.append(f"{path}: expected {schema_type}, got {type(instance).__name__}")
            return

    if "enum" in schema and instance not in schema["enum"]:
        errors.append(f"{path}: '{instance}' is not one of {schema['enum']}")

    if schema_type == "string":
        if "pattern" in schema and not re.match(schema["pattern"], instance):
            errors.append(f"{path}: '{instance}' does not match pattern {schema['pattern']!r}")
        if "minLength" in schema and len(instance) < schema["minLength"]:
            errors.append(f"{path}: length {len(instance)} < minLength {schema['minLength']}")
        if "format" in schema:
            _check_format(instance, schema["format"], path, errors)

    if schema_type in ("integer", "number"):
        if "minimum" in schema and instance < schema["minimum"]:
            errors.append(f"{path}: {instance} < minimum {schema['minimum']}")
        if "maximum" in schema and instance > schema["maximum"]:
            errors.append(f"{path}: {instance} > maximum {schema['maximum']}")

    if schema_type == "object":
        required = schema.get("required", [])
        for key in required:
            if key not in instance:
                errors.append(f"{path}: missing required property '{key}'")
        properties = schema.get("properties", {})
        additional_allowed = schema.get("additionalProperties", True)
        for key, value in instance.items():
            if key in properties:
                _validate_node(value, properties[key], f"{path}.{key}", errors)
            elif not additional_allowed:
                errors.append(f"{path}: unexpected property '{key}'")

    if schema_type == "array":
        item_schema = schema.get("items")
        min_items = schema.get("minItems")
        if min_items is not None and len(instance) < min_items:
            errors.append(f"{path}: has {len(instance)} items, minItems is {min_items}")
        if item_schema is not None:
            for i, item in enumerate(instance):
                _validate_node(item, item_schema, f"{path}[{i}]", errors)
