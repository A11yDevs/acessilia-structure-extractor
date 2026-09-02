# API

## Overview

The Acessilia Structure Extractor exposes its functionality through:

1. **CLI** — command-line interface for direct use
2. **REST API** — HTTP endpoints for programmatic consumption (planned)
3. **MCP** — tools for AI agents (planned)

## CLI

The command-line interface is the current primary means of interaction.

### Basic Usage

```bash
# Extract structure from a PDF
acessilia-extract document.pdf

# Specify output
acessilia-extract document.pdf -o result.json

# Use remote docling-serve
acessilia-extract document.pdf --docling-serve http://localhost:5001

# Disable OCR
acessilia-extract document.pdf --no-ocr

# Specify language
acessilia-extract document.pdf --language en-US

# Validate against a specific schema
acessilia-extract document.pdf --schema custom-schema.json
```

### Default Behavior

- **Input**: PDF, DOCX, images (any format supported by Docling)
- **Output**: `<document>.processing-manifest.json` in the same directory
- **Schema**: automatic validation against `schemas/processing_manifest.schema.json`
- **Language**: `pt-BR` (default)

### Exit Codes

| Code | Meaning |
|---|---|
| `0` | Success |
| `1` | Manifest validation error |
| `2` | Extraction error |

## REST API

The REST API is in the planning phase. Below is the proposed design.

### Planned Endpoints

| Method | Route | Description |
|---|---|---|
| `POST` | `/v1/extract` | Submit document for extraction |
| `GET` | `/v1/extract/{task_id}` | Extraction status and result |
| `GET` | `/v1/health` | Service health check |
| `GET` | `/v1/schema` | Returns the Processing Manifest JSON Schema |

### POST /v1/extract

**Request**:

```http
POST /v1/extract HTTP/1.1
Content-Type: multipart/form-data

file: <document.pdf>
language: pt-BR
ocr: true
```

**Response** (202 Accepted):

```json
{
    "task_id": "extract-abc123",
    "status": "queued",
    "position": 1
}
```

### GET /v1/extract/{task_id}

**Response** (200 OK — completed):

```json
{
    "task_id": "extract-abc123",
    "status": "completed",
    "manifest": { ... }
}
```

**Response** (200 OK — processing):

```json
{
    "task_id": "extract-abc123",
    "status": "processing",
    "progress": 0.65
}
```

### GET /v1/health

```json
{
    "status": "ok",
    "version": "0.1.0",
    "backends": {
        "docling": true,
        "docling-serve": "http://docling-serve:5001"
    }
}
```

## MCP (Model Context Protocol)

MCP support is in the planning phase. It will allow AI agents (including the Acessilia orchestrator) to consume structural extraction as tools.

### Planned Tools

| Tool | Description |
|---|---|
| `extract_document` | Extract structure from a document |
| `get_manifest` | Retrieve a processed manifest |
| `list_backends` | List available extraction backends |

### Example Usage (MCP)

```json
{
    "tool": "extract_document",
    "arguments": {
        "source": "document.pdf",
        "language": "pt-BR"
    }
}
```

## Processing Manifest

The **Processing Manifest** is the central API contract. Every processed document produces a JSON manifest validated against the schema at `schemas/processing_manifest.schema.json`.

### Structure

```json
{
    "$schema": "urn:a11y-devs:schema:processing-manifest:1.1.0",
    "schema_version": "1.1.0",
    "manifest_id": "manifest-abc123-r1",
    "revision": 1,
    "status": "extracted",
    "created_at": "2026-07-27T12:00:00Z",
    "source": {
        "document_id": "doc-abc123",
        "filename": "document.pdf",
        "path": "/path/to/document.pdf",
        "media_type": "application/pdf",
        "byte_size": 102400,
        "sha256": "abcdef..."
    },
    "extractor": {
        "name": "docling",
        "version": "2.x",
        "started_at": "2026-07-27T12:00:00Z",
        "completed_at": "2026-07-27T12:00:05Z",
        "duration_ms": 5000,
        "configuration": { "ocr": true }
    },
    "title": "Document Title",
    "language": "pt-BR",
    "pages": [ ... ],
    "elements": [ ... ],
    "observations": [ ... ],
    "obligations": [ ... ],
    "artifacts": [ ... ],
    "summary": {
        "page_count": 10,
        "element_count": 150,
        "observation_count": 3,
        "obligation_count": 5,
        "element_types": {
            "heading": 20,
            "paragraph": 80,
            "table": 5,
            "picture": 3,
            "list_item": 30,
            "formula": 2,
            "caption": 10
        }
    }
}
```

### Elements

Each structural element of the document is represented as a `ManifestElement`:

| Field | Type | Description |
|---|---|---|
| `id` | string | Unique identifier |
| `type` | enum | Canonical type (title, heading, paragraph, table, picture, etc.) |
| `raw_label` | string | Original extractor label |
| `reading_order` | integer | Reading order (1-based) |
| `hierarchy_level` | integer | Hierarchy level (0 = root) |
| `text` | string | Textual content (sanitized) |
| `page_number` | integer | Page number |
| `confidence` | float | Extraction confidence (0-1) |
| `provenance` | array | Provenance (bbox, characters) |
| `metadata` | object | Type-specific metadata (table_ast, etc.) |

### Obligations

The manifest identifies **accessibility obligations** that need to be fulfilled:

| Element Type | Obligation | Admissible Methods |
|---|---|---|
| `picture` | `describe-image` | vision-description, human-review |
| `table` | `linearize-table` | docling-table, pandoc-table, human-review |
| `formula` | `verbalize-formula` | mathml, latex-verbalizer, human-review |
| `code` | `preserve-code-semantics` | pandoc-code, human-review |
| `unknown` | `review-structure` | docling-retry, pymupdf-region, human-review |

### Schema

The JSON Schema Draft 2020-12 is at `schemas/processing_manifest.schema.json` and can be generated programmatically:

```python
from acessilia_extractor.manifest.schema import processing_manifest_schema

schema = processing_manifest_schema()
```

## Consumers

### Acessilia Orchestrator

The central [Acessilia](https://github.com/A11yDevs/acessilia) project consumes the Structure Extractor to obtain the canonical document structure before applying the transformation pipeline to accessible formats.

### Specialized Agents

AI agents (e.g., image description agent, table linearization agent) consume the manifest to identify elements requiring processing.

### External Applications

Any application can consume the Processing Manifest via REST API or MCP to obtain document structure without directly depending on Docling.