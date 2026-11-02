"""Source registry: load, validate, and index public-data source
descriptions.

A "source" is metadata about *where data comes from* (an agency, a
homepage, a license, an access method) -- not the data itself. Building
this registry, plus acquisition recipes (recipes.py) and field-level
provenance (provenance.py), is this mission's deliverable: the core
that must exist and be reproducible before any bulk data acquisition
happens against real sources.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from publicgraph.schemas import SOURCE_SCHEMA
from publicgraph.validation import validate

DEFAULT_SOURCES_DIR = Path(__file__).parent / "data" / "sources"


class RegistryError(ValueError):
    """Raised for invalid or inconsistent registry data."""


@dataclass(frozen=True)
class Source:
    id: str
    name: str
    agency: str
    homepage_url: str
    license: str
    access_method: str
    formats: tuple[str, ...]
    update_cadence: str
    added_at: str
    license_url: str | None = None
    terms_of_use_notes: str | None = None
    notes: str | None = None

    @classmethod
    def from_dict(cls, data: dict) -> "Source":
        return cls(
            id=data["id"],
            name=data["name"],
            agency=data["agency"],
            homepage_url=data["homepage_url"],
            license=data["license"],
            access_method=data["access_method"],
            formats=tuple(data["formats"]),
            update_cadence=data["update_cadence"],
            added_at=data["added_at"],
            license_url=data.get("license_url"),
            terms_of_use_notes=data.get("terms_of_use_notes"),
            notes=data.get("notes"),
        )


def validate_source_dict(data: dict) -> list[str]:
    """Return a list of validation errors (empty if valid)."""
    return validate(data, SOURCE_SCHEMA)


def load_source_file(path: Path) -> Source:
    data = json.loads(path.read_text())
    errors = validate_source_dict(data)
    if errors:
        raise RegistryError(f"{path}: " + "; ".join(errors))
    return Source.from_dict(data)


@dataclass
class Registry:
    sources: dict[str, Source] = field(default_factory=dict)

    def __len__(self) -> int:
        return len(self.sources)

    def __contains__(self, source_id: str) -> bool:
        return source_id in self.sources

    def get(self, source_id: str) -> Source:
        try:
            return self.sources[source_id]
        except KeyError:
            raise RegistryError(f"unknown source id: {source_id!r}") from None


def load_registry(sources_dir: Path = DEFAULT_SOURCES_DIR) -> Registry:
    """Load and validate every ``*.json`` source file in ``sources_dir``.

    Raises RegistryError on schema violations or duplicate ids -- the
    registry is meant to fail loudly and immediately rather than let a
    bad source definition through, since acquisition recipes and field
    assertions depend on it for referential integrity. By convention
    each file is named ``<id>.json``, but the id inside the file (not
    the filename) is authoritative.
    """
    registry = Registry()
    for path in sorted(sources_dir.glob("*.json")):
        source = load_source_file(path)
        if source.id in registry.sources:
            raise RegistryError(f"duplicate source id {source.id!r}: also defined in {path}")
        registry.sources[source.id] = source
    return registry
