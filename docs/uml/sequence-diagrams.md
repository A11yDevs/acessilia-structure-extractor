# Sequence Diagrams

## Overview

This document contains sequence diagrams for the key interaction flows of the **Acessilia Structure Extractor**. Each diagram illustrates the message exchange between components for a specific scenario.

## 1. Document Extraction (CLI — Local Docling) [Legacy]

> **Note**: This flow uses local Docling installation. The **recommended** flow is via docling-serve (see diagram 2 below).

```mermaid
sequenceDiagram
    participant User as Developer
    participant CLI as CLI
    participant Extractor as DoclingManifestExtractor
    participant Docling as Docling Pipeline
    participant Builder as Manifest Builder
    participant Pipeline as Text Pipeline
    participant Schema as Schema Validator
    participant FS as File System

    User->>CLI: acessilia-extract document.pdf
    CLI->>CLI: Parse arguments
    CLI->>Extractor: instantiate(enable_ocr=True)
    CLI->>Extractor: extract(document.pdf)

    Extractor->>Extractor: resolve path, check file exists
    Extractor->>Docling: create_converter()
    Docling-->>Extractor: DocumentConverter

    Extractor->>Docling: convert_document(converter, path)
    Docling->>Docling: Parse PDF
    Docling->>Docling: Layout analysis
    Docling->>Docling: OCR (if enabled)
    Docling->>Docling: Table structure detection
    Docling->>Docling: Reading order
    Docling-->>Extractor: DoclingDocument

    Extractor-->>CLI: DoclingExtraction

    CLI->>Builder: build_processing_manifest(source, extraction)

    Builder->>Builder: Map labels to canonical types
    Builder->>Pipeline: sanitize_text(text)
    Pipeline-->>Builder: sanitized text
    Builder->>Pipeline: normalize_table_ast(raw_table)
    Pipeline-->>Builder: canonical table AST
    Builder->>Builder: Build elements list
    Builder->>Builder: Build pages list
    Builder->>Builder: Derive observations
    Builder->>Builder: Derive obligations
    Builder->>Builder: Build summary
    Builder-->>CLI: ProcessingManifest

    CLI->>Schema: validate_manifest(payload, schema_path)
    Schema->>Schema: Pydantic validation
    Schema->>Schema: JSON Schema validation
    Schema-->>CLI: validation errors (if any)

    CLI->>FS: write output JSON
    CLI-->>User: Processing Manifest (JSON)
```

## 2. Document Extraction (CLI — Remote docling-serve) ★

> **Default flow**: This is the recommended extraction path. It requires Docker for docling-serve but avoids local ML dependencies.

```mermaid
sequenceDiagram
    participant User as Developer
    participant CLI as CLI
    participant Extractor as DoclingServeExtractor
    participant Serve as docling-serve
    participant Builder as Manifest Builder
    participant Schema as Schema Validator
    participant FS as File System

    User->>CLI: acessilia-extract document.pdf --docling-serve http://serve:5001
    CLI->>CLI: Parse arguments
    CLI->>Extractor: instantiate(base_url="http://serve:5001")
    CLI->>Extractor: extract(document.pdf)

    Extractor->>Extractor: resolve path, check file exists
    Extractor->>Serve: POST /v1/convert/file (multipart)
    Serve->>Serve: Process document
    Serve-->>Extractor: JSON with DoclingDocument

    Extractor->>Extractor: Wrap in _BuildDoclingDocument
    Extractor-->>CLI: DoclingExtraction

    CLI->>Builder: build_processing_manifest(source, extraction)
    Builder-->>CLI: ProcessingManifest

    CLI->>Schema: validate_manifest(payload)
    Schema-->>CLI: validation result

    CLI->>FS: write output JSON
    CLI-->>User: Processing Manifest (JSON)
```

## 3. Snapshot Validation

```mermaid
sequenceDiagram
    participant Dev as Developer
    participant Script as validate_snapshots.py
    participant Extractor as DoclingServeExtractor
    participant Serve as docling-serve
    participant Comparator as Snapshot Comparator
    participant FS as File System

    Dev->>Script: python validate_snapshots.py

    Script->>Script: Read manifest.csv
    Script->>Script: Filter documents (≤ 40 pages)

    loop For each document
        Script->>Extractor: extract(document_path)
        Extractor->>Serve: POST /v1/convert/file
        Serve-->>Extractor: DoclingDocument JSON
        Extractor-->>Script: DoclingExtraction

        Script->>Script: build_processing_manifest()
        Script->>FS: write actual snapshot

        Script->>Comparator: compare_manifests(actual, expected)
        Comparator->>Comparator: Strip volatile fields
        Comparator->>Comparator: Compare semantic structure
        Comparator-->>Script: diff report
    end

    Script-->>Dev: Validation summary
```

## 4. REST API (Planned) — Async Extraction Flow

```mermaid
sequenceDiagram
    participant Client as Client
    participant API as REST API
    participant Queue as Task Queue
    participant Worker as Extraction Worker
    participant Backend as Extraction Backend
    participant Store as Result Store

    Client->>API: POST /v1/extract (multipart)
    API->>Queue: enqueue task
    API-->>Client: 202 Accepted { task_id, status: "queued" }

    Client->>API: GET /v1/extract/{task_id}
    API->>Queue: check status
    Queue-->>API: status: "queued"
    API-->>Client: 200 OK { status: "queued", position: 1 }

    Queue->>Worker: dequeue task
    Worker->>Backend: extract(document)
    Backend-->>Worker: DoclingExtraction

    Worker->>Worker: build_processing_manifest()
    Worker->>Store: save result

    Client->>API: GET /v1/extract/{task_id}
    API->>Store: retrieve result
    Store-->>API: Processing Manifest
    API-->>Client: 200 OK { status: "completed", manifest: {...} }
```

## 5. MCP (Planned) — AI Agent Consumption

```mermaid
sequenceDiagram
    participant Agent as AI Agent
    participant MCP as MCP Server
    participant Extractor as Structure Extractor
    participant Manifest as Manifest Builder

    Agent->>MCP: extract_document(source="document.pdf")
    MCP->>Extractor: extract(document.pdf)
    Extractor-->>MCP: DoclingExtraction

    MCP->>Manifest: build_processing_manifest()
    Manifest-->>MCP: ProcessingManifest

    MCP-->>Agent: Processing Manifest (JSON)

    Agent->>Agent: Analyze manifest for obligations
    Agent->>MCP: get_manifest(task_id)
    MCP-->>Agent: Processing Manifest (cached)
```

## 6. Obligation Derivation Flow

```mermaid
sequenceDiagram
    participant Builder as Manifest Builder
    participant Elements as Element List
    participant Obligations as Obligation List

    Builder->>Elements: iterate extracted elements

    loop Each element
        Elements-->>Builder: element (type, metadata)

        alt type == "picture"
            Builder->>Obligations: create "describe-image" obligation
        else type == "table"
            Builder->>Obligations: create "linearize-table" obligation
        else type == "formula"
            Builder->>Obligations: create "verbalize-formula" obligation
        else type == "code"
            Builder->>Obligations: create "preserve-code-semantics" obligation
        else type == "unknown"
            Builder->>Obligations: create "review-structure" obligation
        end
    end

    Builder->>Builder: Detect callout groups
    alt callout group detected
        Builder->>Obligations: create "review-structure" for group
    end

    Builder-->>Obligations: complete obligation list
```

## 7. Dual Validation Flow

```mermaid
sequenceDiagram
    participant CLI as CLI
    participant Pydantic as Pydantic Validator
    participant JSONSchema as JSON Schema Validator
    participant User as Developer

    CLI->>CLI: Build manifest payload

    CLI->>Pydantic: ProcessingManifest.model_validate(payload)
    Pydantic->>Pydantic: Validate types, constraints, references
    Pydantic->>Pydantic: Validate dependency graph (no cycles)
    Pydantic->>Pydantic: Validate summary counts
    alt Validation error
        Pydantic-->>CLI: ValidationError
        CLI-->>User: Error messages
    else Success
        Pydantic-->>CLI: Validated model
    end

    CLI->>JSONSchema: Draft202012Validator(schema).iter_errors(payload)
    JSONSchema->>JSONSchema: Validate against versioned schema
    alt Schema violation
        JSONSchema-->>CLI: Validation errors
        CLI-->>User: Error messages
    else Valid
        JSONSchema-->>CLI: No errors
        CLI-->>User: Success
    end
```