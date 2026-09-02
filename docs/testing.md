# Testing

## Overview

The test suite validates the canonical Processing Manifest and the integration with document extraction services.

| Suite | Location | External dependencies |
|---|---|---|
| Unit tests | `tests/test_processing_manifest.py` | None |
| Snapshot integration tests | `tests/test_snapshot.py` | docling-serve and the dataset submodule |
| Snapshot validation script | `scripts/validate_snapshots.py` | docling-serve and the dataset submodule |

Install the development dependencies before running tests:

```bash
pip install ".[dev]"
```

When using the repository virtual environment, invoke tests with `.venv/bin/python` to ensure Python 3.11 or later is used:

```bash
.venv/bin/python -m pytest --version
```

## Dataset Submodule

The repository includes `tests/dataset` as the `A11yDevs/acessilia-dataset` Git submodule. Only the snapshot-based checks require it.

| Test path | Uses `tests/dataset` | Notes |
|---|---|---|
| `tests/test_processing_manifest.py` | No | Uses fake documents and temporary files only. |
| `tests/test_snapshot.py` | Yes | Reads source documents and expected manifests from the submodule. |
| `scripts/validate_snapshots.py` | Yes | Reads fixtures, writes actual snapshots, and compares expected manifests. |

The snapshot checks read `tests/dataset/input/manifest.csv`, the source files in `tests/dataset/input`, and expected results in `tests/dataset/intermediate/processing-manifest`.

If the submodule is unavailable, `tests/test_snapshot.py` is skipped; the unit suite remains runnable. Initialize or refresh the dataset before running snapshot checks:

```bash
git submodule update --init tests/dataset
```

## Unit Tests

`tests/test_processing_manifest.py` contains fast, deterministic tests that use in-memory fake documents. Docker, Docling, and the dataset are not required.

The suite covers:

- construction of a valid Processing Manifest;
- JSON Schema Draft 2020-12 generation and validation;
- validation of references to manifest elements;
- preservation of code block text;
- table AST normalization and metadata extraction.

Run only the unit suite:

```bash
.venv/bin/python -m pytest tests/test_processing_manifest.py -q
```

### Versioned JSON Schema

The unit suite compares the schema generated from the Pydantic models with `schemas/processing_manifest.schema.json`. When a manifest model changes, regenerate the schema before running the suite:

```bash
.venv/bin/python -c "from pathlib import Path; from acessilia_extractor.manifest.schema import write_processing_manifest_schema; write_processing_manifest_schema(Path('schemas/processing_manifest.schema.json'))"
```

## Snapshot Integration Tests

`tests/test_snapshot.py` submits real documents from the `acessilia-dataset` submodule to docling-serve and compares the resulting manifests with the versioned expected snapshots in `tests/dataset/intermediate/processing-manifest`.

The comparator in `tests/snapshot_comparator.py` ignores volatile values such as timestamps, IDs, paths, checksums, confidence values, and absolute coordinates. It compares the stable semantic structure, including element types, labels, hierarchy, page order, summaries, and obligations.

### Prerequisites

Initialize the dataset submodule if it is not available:

```bash
git submodule update --init tests/dataset
```

Start docling-serve and confirm that it is ready:

```bash
docker start docling-serve
curl --fail http://localhost:5001/health
```

Alternatively, use the project Compose configuration, which creates the service when necessary:

```bash
docker compose -f docker-compose.test-snapshot.yml up -d docling-serve
```

### Run the Snapshot Tests

For a locally exposed docling-serve instance:

```bash
DOCLING_SERVE_URL=http://localhost:5001 \
  .venv/bin/python -m pytest tests/test_snapshot.py -v
```

The tests are skipped when the dataset or compatible document fixtures are unavailable.

## Snapshot Validation Script

The validation script processes all eligible dataset documents, writes the generated manifests to `tests/snapshots`, and compares them with the expected outputs. It skips documents with more than 40 pages.

Run it against docling-serve:

```bash
.venv/bin/python scripts/validate_snapshots.py \
  --backend serve \
  --docling-serve http://localhost:5001
```

Use Compose to run the same validation in an isolated container environment:

```bash
docker compose -f docker-compose.test-snapshot.yml up --build validator
```

### Updating Expected Snapshots

Only update snapshots after reviewing an intentional extraction or manifest-contract change:

```bash
.venv/bin/python scripts/validate_snapshots.py \
  --backend serve \
  --docling-serve http://localhost:5001 \
  --update
```

The script currently retains a legacy `--backend local` option that depends on the removed local Docling extractor. Use `--backend serve` until that legacy path is removed.

## Full Suite

Run all available tests after starting docling-serve:

```bash
DOCLING_SERVE_URL=http://localhost:5001 \
  .venv/bin/python -m pytest tests/ -v
```

## Current Coverage Gaps

The suite does not yet cover the multi-backend architecture introduced by the extractor registry. Add focused tests before registering each new service:

- backend resolution and environment-variable precedence in `backend_registry.py`;
- CLI behavior for `--backend`, backend URLs, and `--list-backends`;
- HTTP error handling and response adaptation for each remote extractor;
- conversions from backend-specific responses, such as GROBID TEI XML, into the canonical manifest;
- end-to-end Compose profiles for each additional backend service.
