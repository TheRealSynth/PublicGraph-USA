"""Field-level provenance and confidence.

A FieldAssertion says: "for this entity, this field has this value,
according to this source (and optionally this recipe run), observed at
this time, with this confidence." Modeling assertions instead of a flat
merged table is deliberate -- the same field can be asserted by more
than one source with different values, and the moat's value comes from
keeping every claim traceable back to where it came from rather than
silently overwriting one source's value with another's.

This module intentionally does not implement conflict *resolution*
(choosing a winning value). That is a downstream, source-comparison
decision that deserves its own mission once there is more than one real
source feeding the same fields; this core only needs to detect and
surface conflicts.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from publicgraph.registry import Registry, RegistryError
from publicgraph.schemas import FIELD_ASSERTION_SCHEMA
from publicgraph.validation import validate

DEFAULT_ASSERTIONS_DIR = Path(__file__).parent / "data" / "assertions"

CONFIDENCE_BANDS = (
    (0.85, "high"),
    (0.5, "medium"),
    (0.0, "low"),
)


class ProvenanceError(ValueError):
    """Raised for invalid or inconsistent provenance data."""


def confidence_band(confidence: float) -> str:
    """Bucket a numeric confidence into a qualitative band for human
    review/reporting. The numeric value remains the source of truth;
    this is a presentation convenience only."""
    if not 0.0 <= confidence <= 1.0:
        raise ValueError(f"confidence must be in [0, 1], got {confidence}")
    for threshold, label in CONFIDENCE_BANDS:
        if confidence >= threshold:
            return label
    raise AssertionError("unreachable: CONFIDENCE_BANDS must bottom out at 0.0")


@dataclass(frozen=True)
class FieldAssertion:
    entity_id: str
    field_name: str
    value: object
    source_id: str
    method: str
    confidence: float
    observed_at: str
    recipe_id: str | None = None
    notes: str | None = None

    @classmethod
    def from_dict(cls, data: dict) -> "FieldAssertion":
        return cls(
            entity_id=data["entity_id"],
            field_name=data["field_name"],
            value=data["value"],
            source_id=data["source_id"],
            method=data["method"],
            confidence=data["confidence"],
            observed_at=data["observed_at"],
            recipe_id=data.get("recipe_id"),
            notes=data.get("notes"),
        )

    @property
    def band(self) -> str:
        return confidence_band(self.confidence)


def validate_assertion_dict(data: dict) -> list[str]:
    return validate(data, FIELD_ASSERTION_SCHEMA)


def load_assertion_file(path: Path, registry: Registry | None = None) -> FieldAssertion:
    data = json.loads(path.read_text())
    errors = validate_assertion_dict(data)
    if errors:
        raise ProvenanceError(f"{path}: " + "; ".join(errors))
    assertion = FieldAssertion.from_dict(data)
    if registry is not None:
        try:
            registry.get(assertion.source_id)
        except RegistryError as exc:
            raise ProvenanceError(f"{path}: {exc}") from exc
    return assertion


def load_assertions(
    assertions_dir: Path = DEFAULT_ASSERTIONS_DIR,
    registry: Registry | None = None,
) -> list[FieldAssertion]:
    return [
        load_assertion_file(path, registry=registry)
        for path in sorted(assertions_dir.glob("*.json"))
    ]


def find_conflicts(
    assertions: list[FieldAssertion],
) -> dict[tuple[str, str], list[FieldAssertion]]:
    """Group assertions by (entity_id, field_name) and return only the
    groups where more than one *distinct* value is asserted."""
    by_key: dict[tuple[str, str], list[FieldAssertion]] = {}
    for assertion in assertions:
        key = (assertion.entity_id, assertion.field_name)
        by_key.setdefault(key, []).append(assertion)
    return {
        key: group
        for key, group in by_key.items()
        if len({a.value for a in group}) > 1
    }
