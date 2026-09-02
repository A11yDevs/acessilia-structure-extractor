# Project Constitution

## Identity

**Name**: Acessilia Structure Extractor
**Purpose**: Document structure extraction service for the Acessilia ecosystem
**License**: MIT
**Language**: Python >= 3.11
**Primary Schema**: `urn:a11y-devs:schema:processing-manifest:1.1.0`

## Objective

Extract, normalize, and expose the structural information of documents (PDF, DOCX, images) in a canonical, machine-readable representation — the **Processing Manifest** — while isolating heavy dependencies (Docling, ML models) from the main Acessilia runtime.

## Principles

### 1. Canonical Contract

The **Processing Manifest** is the sole contract between extractors and consumers. No consumer shall depend on Docling's internal structures or any specific backend.

```python
# ✅ Correct: consume the Processing Manifest
manifest = process_manifest(document)
for element in manifest.elements:
    process(element)

# ❌ Incorrect: depend on Docling structures
docling_doc = convert_docling(document)
for item in docling_doc.texts:  # coupling to Docling
    process(item)
```

### 2. Abstract Interface

Every extraction backend implements `BaseExtractor`. Adding a new backend must never require changes to the builder or consumers.

```python
class BaseExtractor(ABC):
    @abstractmethod
    def extract(self, source_path: Path) -> DoclingExtraction:
        ...
```

### 3. Separation of Concerns

- **Extractors**: communication with backends (docling-serve, Docling, PyMuPDF)
- **Manifest**: construction, models, validation of the Processing Manifest
- **Pipeline**: sanitization, table normalization
- **CLI**: user interface
- **Tests**: behavior validation

### 4. Rigorous Validation

Every generated manifest must be validated at two levels:

1. **Pydantic**: type validation, constraints, and references
2. **JSON Schema**: validation against a versioned Draft 2020-12 schema

### 5. Compatibility with the Acessilia Ecosystem

The Structure Extractor is part of the [Acessilia](https://github.com/A11yDevs/acessilia) ecosystem. It must:

- Produce manifests that the Acessilia orchestrator can consume
- Expose interfaces (REST, MCP) compatible with the central project's architecture
- Follow the same naming conventions and versioning

## Schemas

### Processing Manifest

| Field | Version | URI |
|---|---|---|
| `$schema` | 1.1.0 | `urn:a11y-devs:schema:processing-manifest:1.1.0` |

The schema is generated from the Pydantic models and maintained at `schemas/processing_manifest.schema.json`.

### Semantic Versioning

The Processing Manifest schema follows [SemVer](https://semver.org/):

- **Major**: structural changes that break compatibility
- **Minor**: addition of optional fields
- **Patch**: validation fixes without contract changes

## Language

### Code

- **Python** >= 3.11 with mandatory type hints
- Code identifiers (classes, functions, variables) in **English**
- Docstrings in **English** (international audience)
- Code comments in **English**

### Documentation

- All technical documentation in **English** (target audience: international developers)
- The `README.md` and public interfaces are in English
- The software is designed for future internationalization (i18n)

### Commits and Communication

- Commit messages in **English** (Conventional Commits)
- Issues and PRs in **English**

## Dependencies

### Base (required)

| Package | Version | Usage |
|---|---|---|
| `pydantic` | >=2 | Data models and validation |
| `jsonschema` | — | Draft 2020-12 validation |
| `httpx` | >=0.28 | HTTP client (docling-serve) |
| `PyMuPDF` | — | Lightweight extraction (planned) |

### Optional

| Extra | Packages | Usage |
|---|---|---|
| `[docling]` | docling>=2, torch, rapidocr | Full extraction pipeline |
| `[docling-serve]` | docling-core>=2, httpx | Client for remote docling-serve |
| `[dev]` | pytest>=7, pytest-asyncio | Development and testing |

## Build Structure

### Docker

Multi-stage build with specific targets:

| Target | Base | Docling | Usage |
|---|---|---|---|
| `base` | python:3.11-slim | ❌ | Minimal base image |
| `production` | base | ❌ | **Default** — uses remote docling-serve |
| `with-docling` | base | ✅ | Legacy — local Docling (not recommended) |
| `production-docling` | with-docling | ✅ | Production with Docling |

| `test` | base | ❌ | Unit tests |
| `validate-snapshots` | with-docling | ✅ | Snapshot validation |

### Publishing

The package is published as `acessilia-structure-extractor` on PyPI (planned). Currently distributed via GitHub Container Registry as a Docker image.

## Governance

### Maintainers

- [Jhonata Fernandes Cordeiro](https://github.com/jhonata192)
- [Marcelo Inuzuka](https://github.com/marceloakira)

### Decision Process

1. Issues and discussions guide the roadmap
2. Significant changes require a reviewed PR
3. The Processing Manifest schema requires maintainer approval for changes

## Related Repositories

| Repository | Relationship |
|---|---|
| [A11yDevs/acessilia](https://github.com/A11yDevs/acessilia) | Central project — consumes the Structure Extractor |
| [A11yDevs/acessilia-dataset](https://github.com/A11yDevs/acessilia-dataset) | Document dataset for testing (submodule) |
| [docling-project/docling](https://github.com/docling-project/docling) | Document understanding engine (used via docling-serve) |
| [docling-project/docling-serve](https://github.com/docling-project/docling-serve) | Docling REST server |