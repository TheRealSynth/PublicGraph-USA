"""Schema definitions for the three core record types.

Kept as plain dicts (rather than files loaded via a packaging mechanism)
so the package works by simple sys.path insertion, with no install step
and no root-level packaging manifest -- see __init__.py.
"""

SOURCE_ID_PATTERN = r"^[a-z0-9]+(-[a-z0-9]+)*$"

ACCESS_METHODS = ["http_api", "bulk_download", "ftp", "scrape", "manual"]
UPDATE_CADENCES = [
    "continuous",
    "daily",
    "weekly",
    "monthly",
    "quarterly",
    "annual",
    "irregular",
    "static",
]

SOURCE_SCHEMA = {
    "type": "object",
    "required": [
        "id",
        "name",
        "agency",
        "homepage_url",
        "license",
        "access_method",
        "formats",
        "update_cadence",
        "added_at",
    ],
    "additionalProperties": False,
    "properties": {
        "id": {"type": "string", "pattern": SOURCE_ID_PATTERN, "minLength": 2},
        "name": {"type": "string", "minLength": 1},
        "agency": {"type": "string", "minLength": 1},
        "homepage_url": {"type": "string", "pattern": r"^https://"},
        "license": {"type": "string", "minLength": 1},
        "license_url": {"type": "string", "pattern": r"^https://"},
        "access_method": {"type": "string", "enum": ACCESS_METHODS},
        "formats": {"type": "array", "minItems": 1, "items": {"type": "string"}},
        "update_cadence": {"type": "string", "enum": UPDATE_CADENCES},
        "terms_of_use_notes": {"type": "string"},
        "added_at": {"type": "string", "format": "date"},
        "notes": {"type": "string"},
    },
}

RECIPE_STEP_TYPES = ["http_get"]

RECIPE_STEP_SCHEMA = {
    "type": "object",
    "required": ["type", "url", "output_relpath"],
    "additionalProperties": False,
    "properties": {
        "type": {"type": "string", "enum": RECIPE_STEP_TYPES},
        "url": {"type": "string", "pattern": r"^https://"},
        "params": {"type": "object", "additionalProperties": True},
        "output_relpath": {"type": "string", "minLength": 1},
        "expected_content_type": {"type": "string"},
    },
}

RECIPE_SCHEMA = {
    "type": "object",
    "required": ["id", "source_id", "version", "description", "steps", "checksum_algorithm"],
    "additionalProperties": False,
    "properties": {
        "id": {"type": "string", "pattern": SOURCE_ID_PATTERN, "minLength": 2},
        "source_id": {"type": "string", "pattern": SOURCE_ID_PATTERN, "minLength": 2},
        "version": {"type": "integer", "minimum": 1},
        "description": {"type": "string", "minLength": 1},
        "steps": {"type": "array", "minItems": 1, "items": RECIPE_STEP_SCHEMA},
        "checksum_algorithm": {"type": "string", "enum": ["sha256"]},
        "retry_max_attempts": {"type": "integer", "minimum": 1, "maximum": 10},
        "notes": {"type": "string"},
    },
}

ASSERTION_METHODS = ["direct_extraction", "computed", "inferred", "manual_entry"]

FIELD_ASSERTION_SCHEMA = {
    "type": "object",
    "required": [
        "entity_id",
        "field_name",
        "value",
        "source_id",
        "method",
        "confidence",
        "observed_at",
    ],
    "additionalProperties": False,
    "properties": {
        "entity_id": {"type": "string", "minLength": 1},
        "field_name": {"type": "string", "minLength": 1},
        "value": {},  # deliberately untyped: field values vary by entity/field
        "source_id": {"type": "string", "pattern": SOURCE_ID_PATTERN, "minLength": 2},
        "recipe_id": {"type": "string", "pattern": SOURCE_ID_PATTERN, "minLength": 2},
        "method": {"type": "string", "enum": ASSERTION_METHODS},
        "confidence": {"type": "number", "minimum": 0.0, "maximum": 1.0},
        "observed_at": {"type": "string", "format": "date-time"},
        "notes": {"type": "string"},
    },
}
