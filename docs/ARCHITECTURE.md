# PublicGraph-USA architecture: source registry, acquisition recipes, and provenance/confidence core

Mission: `DATA-CORE-001`. This document records what was built, why, and
what is deliberately left for later missions.

## Starting state

At the time this mission was claimed, `TheRealSynth/PublicGraph-USA` was a
completely empty GitHub repository: no commits, no branches, no README, no
spec documents, and no prior architecture decisions to build on. Mission
`DATA-REPO-001` (state `DONE`) only recorded that this repository is the
mapped target for the "public data moat" project; it did not scaffold any
code or leave any design notes.

This mission's `owns_paths` is `src/**`, `tests/**`, `docs/**`, with no
`acceptance.commands` and no `required_artifacts` specified in the mission
file. Everything in this document is therefore a first, deliberately
conservative implementation of the mission's stated objective ("Build
source registry + reproducible acquisition recipes + field
assertions/provenance/confidence before bulk downloading national data"),
not a response to a pre-existing spec.

## Why nothing lives at the repository root yet

Normally a new repository would get a root `README.md`, a dependency
manifest (`requirements.txt` / `pyproject.toml`), a `.gitignore`, and CI
config immediately. All of those are outside this mission's `owns_paths`
(`src/**`, `tests/**`, `docs/**`), so none of them were added. This mirrors
the scope discipline other missions in this portfolio use (see e.g.
`TheRealSynth/ToolRefinery` mission `TR-AI-REL-001`, which deliberately
left a useful CLI wrapper out of scope because it needed a root-level
file). **A follow-up mission with root-level `owns_paths` should add
`README.md`, `requirements.txt` or `pyproject.toml`, `.gitignore`, and CI**
— see Proposed follow-ups below.

One consequence: this package has **zero third-party dependencies**. It
would normally be reasonable to use `jsonschema` for schema validation and
YAML for the data files, but declaring those dependencies would require a
root-level manifest this mission cannot create. Rather than depend on an
undeclared, unpinned package, `publicgraph/validation.py` implements the
small subset of JSON-Schema-like validation this package actually needs,
and all data files are plain JSON (stdlib `json`, no parser dependency).
This should be revisited once a root-level manifest exists — see follow-ups.

## The three core record types

### 1. Source registry (`publicgraph/registry.py`, `publicgraph/schemas.py: SOURCE_SCHEMA`)

A **source** is metadata about *where data comes from*: an id, a human
name, the responsible agency, a homepage URL, its license, how it's
accessed (`http_api` / `bulk_download` / `ftp` / `scrape` / `manual`), the
formats it's published in, how often it updates, and free-text
terms-of-use notes. It intentionally does not include actual data.

`load_registry()` loads every `*.json` file under
`publicgraph/data/sources/`, validates each against `SOURCE_SCHEMA`, and
fails loudly (`RegistryError`) on the first schema violation or duplicate
id, rather than silently skipping bad entries — recipes and field
assertions both depend on the registry for referential integrity, so a
malformed source definition should stop the whole load rather than
produce a registry with holes in it.

Two illustrative example sources are bundled: `census-acs` (U.S. Census
Bureau, American Community Survey) and `bls-cpi` (U.S. Bureau of Labor
Statistics, Consumer Price Index). These are real agencies with real,
stable homepage URLs, but they are explicitly marked in their own
`notes` field as **not yet vetted for a production acquisition recipe**
— their purpose is to exercise the schema and loader end to end, not to
authorize pulling real ACS/CPI data yet. In particular, `terms_of_use_notes`
flags that each source's actual API terms, rate limits, and registration
requirements still need to be confirmed before any real fetch is run
against it.

### 2. Acquisition recipes (`publicgraph/recipes.py`, `publicgraph/runner.py`, `SOURCE_SCHEMA`/`RECIPE_SCHEMA`)

A **recipe** is a declarative, versioned list of steps (currently only
`http_get`) that describe how to fetch raw artifacts from a source. A
recipe never contains inline scraping/parsing logic — the point is that
the same recipe version, run twice, issues exactly the same requests
both times, which is what "reproducible acquisition" means here.

`load_recipes(registry=...)` validates each recipe against
`RECIPE_SCHEMA` and, when a registry is supplied, checks that
`source_id` actually resolves — a recipe pointing at a source that
doesn't exist is a data-integrity bug, not a warning.

`publicgraph/runner.py: run_recipe()` executes a recipe's steps against
any `Fetcher` (see below), retrying a failing step (non-2xx status) up to
`retry_max_attempts` times, writing each fetched artifact under a given
output directory, and returning one `ArtifactProvenance` record per step:
source id, recipe id + version, URL, output path, checksum
(`sha256` by default), HTTP status, content type, fetch timestamp, and
attempt count. That record is the reproducibility evidence: "this exact
byte content, from this URL, at this time, via this recipe version."

One illustrative recipe, `census-acs-homepage-probe`, is bundled. It only
fetches the `census-acs` source's homepage as a smoke test of the
runner/fetcher pipeline; it deliberately does not attempt a real ACS
dataset pull, since no specific dataset/table/endpoint has been vetted yet.

### 3. Field-level provenance and confidence (`publicgraph/provenance.py`, `FIELD_ASSERTION_SCHEMA`)

A **field assertion** says: "for this entity, this field has this value,
according to this source (and optionally this recipe run), observed at
this time, with this confidence in `[0, 1]`." This is deliberately an
assertion log, not a merged table — the same `(entity_id, field_name)`
can be asserted by more than one source with different values, and the
whole point of a provenance-first data moat is to keep every claim
traceable back to where it came from instead of one source silently
overwriting another's value.

`confidence_band()` buckets the numeric confidence into `high` / `medium`
/ `low` for human-facing reporting; the float remains the source of truth
everywhere else. `find_conflicts()` groups assertions by
`(entity_id, field_name)` and returns only the groups with more than one
distinct value — it deliberately does **not** pick a winner. Choosing how
to resolve a real conflict (by confidence, by source authority, by
recency, ...) is a judgment call that deserves its own mission once there
is more than one real source feeding the same fields; this core only
needs to detect and surface conflicts.

Two synthetic (explicitly not real Census/BLS data) example assertions
are bundled for the same fake entity/field, with different values, purely
to exercise `find_conflicts()` end to end. Their `notes` fields say this
outright so nobody mistakes them for real data later.

## What this mission deliberately did not do

- **No bulk data acquisition.** The mission objective is explicit that
  this core comes *before* bulk downloading national data. `HTTPFetcher`
  (a real, stdlib-only network client) exists so a future mission can run
  real recipes, but it is not exercised by the test suite or by any
  bundled recipe against a real dataset endpoint — only against a
  source's homepage, and only as a pipeline smoke test.
- **No conflict resolution policy.** `find_conflicts()` detects, it does
  not resolve. See above.
- **No field-extraction/parsing layer.** Turning a fetched artifact's raw
  bytes into `FieldAssertion`s (HTML/CSV/JSON parsing, per-source
  extraction logic) is out of scope for this core and is real, source-
  specific engineering work for a follow-up mission.
- **No root-level project scaffolding** (`README.md`, dependency manifest,
  `.gitignore`, CI). See "Why nothing lives at the repository root yet."

## Proposed follow-ups

1. A mission scoped to the repository root should add `README.md`, a
   dependency manifest, `.gitignore`, and CI wiring to run `pytest` on
   every push/PR.
2. Once a dependency manifest exists, reassess whether to adopt
   `jsonschema` (already more feature-complete than
   `publicgraph/validation.py`) and/or YAML for data files, or keep the
   current zero-dependency approach deliberately.
3. A source-specific mission should pick one real, narrow dataset (e.g. a
   single ACS table or a single BLS CPI series), confirm its actual API
   terms/rate limits/endpoint shape, and add a real (non-homepage-probe)
   acquisition recipe plus a first extraction pipeline that produces real
   `FieldAssertion`s from it.
4. Once two or more real sources assert the same fields, design and
   implement an actual conflict-resolution policy on top of
   `find_conflicts()`.
