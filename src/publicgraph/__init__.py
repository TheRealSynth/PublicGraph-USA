"""publicgraph: source registry, acquisition recipes, and field-level
provenance/confidence core for the national public-data moat.

This package is deliberately stdlib-only. Mission DATA-CORE-001's
owns_paths is limited to src/**, tests/**, and docs/**, which does not
include a root-level dependency manifest (requirements.txt / pyproject.toml).
Rather than depend on unpinned, undeclared third-party packages, the core
is built entirely on the Python standard library so it is reproducible
with nothing more than a Python interpreter. See docs/ARCHITECTURE.md.
"""

__version__ = "0.1.0"
