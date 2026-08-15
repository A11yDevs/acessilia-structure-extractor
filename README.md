# Acessilia Structure Extractor

[![License: GPL v3+](https://img.shields.io/badge/License-GPL%20v3%2B-blue.svg)](LICENSE)

Structural extraction service for Acessilia, providing document parsing and canonical structure through REST API and MCP.

## Overview

**Acessilia Structure Extractor** is a standalone document-structure extraction service for the [Acessilia](https://github.com/A11yDevs/acessilia) ecosystem.

Its main purpose is to extract, normalize, and expose the structural information of documents while isolating heavyweight document-processing dependencies, such as **Docling** and its models, from the main Acessilia runtime.

The service is intended to be consumed by the Acessilia orchestrator, specialized agents, external applications, and MCP-compatible clients.

## Motivation

Document understanding may require large runtime dependencies and machine learning models. In particular, Docling-based environments can become significantly larger when their models are included in container images.

Separating structural extraction into its own service provides several benefits:

- isolates heavyweight dependencies from the main Acessilia application;
- enables independent deployment and scaling;
- allows extraction models to be cached or stored separately from the application image;
- provides a stable contract to downstream consumers;
- allows extraction engines to evolve independently;
- supports both traditional service integration and agent-based interaction.

## Architecture

```text
                    Clients
                      |
          +-----------+-----------+
          |                       |
       REST API                  MCP
          |                       |
          +-----------+-----------+
                      |
            Structure Extraction
                      |
              Canonical Normalizer
                      |
          +-----------+-----------+
          |                       |
       Docling                  PyMuPDF
          |
        Models
```

The service should expose an **Acessilia canonical document structure** rather than extraction-engine-specific objects.

```text
DoclingDocument
      |
      v
Docling Adapter
      |
      v
Acessilia Canonical Structure
      |
      +-- REST API
      +-- MCP
      +-- Acessilia Orchestrator
      +-- Other consumers
```

This abstraction allows extraction engines to be replaced, upgraded, or combined without requiring changes in downstream components.

## Responsibilities

The service is expected to:

- receive documents for structural analysis;
- identify the logical and visual structure of the content;
- normalize extractor-specific results;
- produce a canonical machine-readable representation;
- expose document structure through REST endpoints;
- expose selected capabilities as MCP tools;
- provide structural information to other Acessilia components.

Possible structural elements include:

- document metadata;
- pages;
- headings and sections;
- paragraphs;
- lists;
- tables;
- figures and images;
- mathematical expressions;
- code blocks;
- footnotes and references;
- reading order;
- relationships between document elements.

## Interfaces

### REST API

The REST API is intended primarily for service-to-service communication.

Planned endpoints may include:

```text
POST /v1/documents/extract
GET  /v1/documents/{id}
GET  /v1/documents/{id}/structure
GET  /v1/documents/{id}/status
```

Example request:

```json
{
  "source": "document.pdf",
  "options": {
    "tables": true,
    "images": true,
    "math": true
  }
}
```

Example response:

```json
{
  "document_id": "example-id",
  "schema_version": "1.0",
  "pages": [],
  "blocks": [],
  "tables": [],
  "images": [],
  "math": []
}
```

The exact API and canonical schema are still under definition.

### MCP

The MCP interface is intended primarily for AI agents and MCP-compatible clients.

Possible tools include:

```text
extract_document_structure
get_document_outline
inspect_page
get_tables
get_figures
get_math_expressions
```

The MCP layer should expose Acessilia-oriented capabilities instead of leaking implementation-specific Docling operations.

## Extraction Backends

The architecture is intended to support multiple extraction backends.

Initial candidates include:

- **Docling** — advanced document parsing and structural understanding;
- **PyMuPDF** — lightweight PDF inspection and extraction;
- other specialized extractors as the project evolves.

Backends should be implemented behind a common internal abstraction.

```text
StructureExtractor
      |
      +-- DoclingExtractor
      +-- PyMuPDFExtractor
      +-- FutureExtractor
```

## Canonical Document Structure

A central goal of the project is to define a stable intermediate representation for document structure.

This representation should be:

- independent of the extraction engine;
- serializable as JSON;
- versioned;
- validated through JSON Schema or equivalent mechanisms;
- suitable for downstream accessibility processing;
- expressive enough to preserve relationships between structural elements.

The canonical structure may later become part of the broader **Acessilia Canonical AST**.

## Deployment

The service is designed to run independently from the main Acessilia application.

```text
Acessilia Planner / Orchestrator
              |
        REST / MCP
              |
              v
Acessilia Structure Extractor
              |
              v
Canonical Document Structure
```

### Model Storage

Large machine learning models should preferably not be permanently embedded into every application image.

A recommended deployment model is:

```text
Container image
  |
  +-- Application
  +-- Runtime dependencies
  +-- Docling
  |
  +----> Persistent model storage
```

Models may be stored in:

- persistent Docker volumes;
- host-mounted directories;
- shared model caches;
- object storage, when appropriate.

This reduces repeated downloads and avoids rebuilding very large container images when only application code changes.

## Relationship with Acessilia

This repository provides a specialized infrastructure capability for the main [Acessilia](https://github.com/A11yDevs/acessilia) project.

A useful separation of responsibilities is:

```text
Planner / Orchestrator
        |
        | decides what must be done
        v
Structure Extraction Service
        |
        | performs structural analysis
        v
Canonical AST / Manifest
        |
        v
Accessibility Processing Agents
```

In this architecture:

> **Agents decide; specialized services execute capabilities.**

The Acessilia planner should not need to know whether structural extraction is performed by Docling, PyMuPDF, or another backend.

## Technology Stack

The initial implementation is expected to use technologies such as:

- Python
- FastAPI
- Model Context Protocol (MCP)
- Docling
- PyMuPDF
- Pydantic
- JSON Schema
- Docker

The stack may evolve as the architecture is validated.

## Project Status

> **Early development / architecture definition**

The project is currently defining its initial architecture, canonical schemas, extraction interfaces, API contracts, and deployment strategy.

Interfaces documented here should therefore be considered provisional.

## Development

Development and local deployment instructions will be added as the initial implementation is established.

A possible future project structure is:

```text
src/
├── api/
├── mcp/
├── extractors/
│   ├── base.py
│   ├── docling.py
│   └── pymupdf.py
├── normalization/
├── schemas/
├── models/
└── services/

tests/
Dockerfile
pyproject.toml
```

## Contributing

Contributions are welcome.

For significant architectural changes, please open an issue first so the proposal can be discussed and aligned with the Acessilia canonical document model and orchestration pipeline.

Contributors retain authorship of their contributions and are expected to contribute code under the same licensing terms adopted by this project.

## Copyright and License

Copyright (C) 2026 Marcelo Inuzuka and Acessilia Structure Extractor contributors

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

See the [LICENSE](LICENSE) file for the full license text.
