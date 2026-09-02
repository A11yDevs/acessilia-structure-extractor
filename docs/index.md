# Acessilia Structure Extractor — Documentation

Welcome to the documentation for the **Acessilia Structure Extractor**, the document structure extraction service of the [Acessilia](https://github.com/A11yDevs/acessilia) ecosystem.

## Overview

The Structure Extractor is an independent microservice responsible for receiving documents (PDF, DOCX, images), analyzing their logical and visual structure, and producing a **Processing Manifest** — a canonical, machine-readable representation of the document content.

It isolates heavy dependencies (Docling, ML models) from the main Acessilia runtime, enabling independent deployment and scaling.

## Documents

| Document | Description |
|---|---|
| [Architecture](architecture.md) | Modules, directories, architectural decisions and diagrams |
| [Installation](installation.md) | Setup, configuration, Docker, build variants |
| [Tools](tools.md) | Docling, PyMuPDF, docling-serve and their features |
| [API](api.md) | REST, MCP, OpenAPI, consumption contracts |
| [Testing](testing.md) | Unit tests, snapshot integration tests, and validation workflow |
| [Contribution](contribution.md) | How to contribute, submitting a PR, coding standards |
| [Constitution](constitution.md) | Language, objective, schemas, project principles |

## Related Repositories

| Repository | Description |
|---|---|
| [A11yDevs/acessilia](https://github.com/A11yDevs/acessilia) | Central project — orchestrator, API, frontends |
| [A11yDevs/acessilia-dataset](https://github.com/A11yDevs/acessilia-dataset) | Document dataset for testing and validation |
| [A11yDevs/acessilia-structure-extractor](https://github.com/A11yDevs/acessilia-structure-extractor) | This repository |

## License

MIT © 2026 Jhonata Fernandes Cordeiro and contributors.