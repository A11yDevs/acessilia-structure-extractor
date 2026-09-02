# Logical and Physical Architecture

## Logical Architecture

The logical architecture describes the system's components, their responsibilities, and the relationships between them, independent of deployment details.

### Component Diagram

```mermaid
graph TB
    subgraph "Presentation Layer"
        CLI[CLI<br/>acessilia-extract]
        REST[REST API<br/>FastAPI - Planned]
        MCP[MCP Server<br/>Planned]
    end

    subgraph "Application Layer"
        EXTRACTOR[Extractor Service]
        BUILDER[Manifest Builder]
        VALIDATOR[Schema Validator]
    end

    subgraph "Domain Layer"
        MODELS[Processing Manifest Models]
        SCHEMA[JSON Schema<br/>Draft 2020-12]
        PIPELINE[Text Pipeline]
    end

    subgraph "Infrastructure Layer"
        DOCLING_SERVE[docling-serve ★]
        DOCLING[Docling Engine<br/>Legacy]
        PYMUPDF[PyMuPDF<br/>Planned]
        FS[File System]
    end

    CLI --> EXTRACTOR
    REST --> EXTRACTOR
    MCP --> EXTRACTOR

    EXTRACTOR --> DOCLING_SERVE
    EXTRACTOR -.-> DOCLING
    EXTRACTOR -.-> PYMUPDF
    EXTRACTOR --> BUILDER

    BUILDER --> PIPELINE
    BUILDER --> MODELS
    BUILDER --> VALIDATOR

    VALIDATOR --> SCHEMA
    VALIDATOR --> MODELS

    PIPELINE --> FS
    EXTRACTOR --> FS
```

### Layer Responsibilities

| Layer | Components | Responsibility |
|---|---|---|
| **Presentation** | CLI, REST API, MCP | Interface with users and external systems |
| **Application** | Extractor Service, Manifest Builder, Schema Validator | Orchestrate extraction and manifest generation |
| **Domain** | Processing Manifest Models, JSON Schema, Text Pipeline | Core business logic and canonical representation |
| **Infrastructure** | docling-serve, Docling, PyMuPDF, File System | External tools and I/O |

### Package Diagram

```mermaid
graph TB
    subgraph "acessilia_extractor"
        CLI_PKG[cli]
        EXTR_PKG[extractors]
        MAN_PKG[manifest]
        PIP_PKG[pipeline]
    end

    subgraph "manifest"
        MODELS[models.py]
        BUILDER_PKG[builder.py]
        SCHEMA_PKG[schema.py]
    end

    subgraph "pipeline"
        SAN[sanitizer.py]
        TBL[table_ast.py]
    end

    CLI_PKG --> EXTR_PKG
    CLI_PKG --> MAN_PKG

    EXTR_PKG --> MAN_PKG

    MAN_PKG --> MODELS
    MAN_PKG --> BUILDER_PKG
    MAN_PKG --> SCHEMA_PKG

    BUILDER_PKG --> PIP_PKG
    BUILDER_PKG --> MODELS
    BUILDER_PKG --> EXTR_PKG

    PIP_PKG --> SAN
    PIP_PKG --> TBL
```

### Class Diagram (Core Domain)

```mermaid
classDiagram
    class BaseExtractor {
        <<abstract>>
        +extract(source_path: Path) DoclingExtraction*
    }

    class DoclingManifestExtractor {
        -enable_ocr: bool
        -_structurer: Any
        +extract(source_path: Path) DoclingExtraction
        -_create_converter() Any
        -_convert_document(converter, path) Any
    }

    class DoclingServeExtractor {
        -base_url: str
        +extract(source_path: Path) DoclingExtraction
    }

    class DoclingExtraction {
        +document: Any
        +started_at: datetime
        +completed_at: datetime
        +duration_ms: int
        +version: str
        +configuration: dict
    }

    class ProcessingManifest {
        +schema_ref: str
        +schema_version: str
        +manifest_id: str
        +revision: int
        +status: str
        +created_at: datetime
        +source: SourceDocument
        +extractor: ExtractorRun
        +title: str
        +language: str
        +pages: list
        +elements: list
        +observations: list
        +obligations: list
        +artifacts: list
        +summary: ManifestSummary
        +validate_references() self
    }

    class SourceDocument {
        +document_id: str
        +filename: str
        +path: str
        +media_type: str
        +byte_size: int
        +sha256: str
    }

    class ExtractorRun {
        +name: str
        +version: str
        +started_at: datetime
        +completed_at: datetime
        +duration_ms: int
        +configuration: dict
    }

    class ManifestElement {
        +id: str
        +type: ElementType
        +raw_label: str
        +reading_order: int
        +hierarchy_level: int
        +text: str
        +page_number: int
        +confidence: float
        +provenance: list
        +metadata: dict
    }

    class Obligation {
        +id: str
        +kind: str
        +status: ObligationStatus
        +selected: bool
        +target_ids: list
        +dependencies: list
        +admissible_methods: list
        +method_costs: dict
        +attempts: list
        +rationale: str
    }

    class ManifestSummary {
        +page_count: int
        +element_count: int
        +observation_count: int
        +obligation_count: int
        +element_types: dict
    }

    BaseExtractor <|-- DoclingManifestExtractor
    BaseExtractor <|-- DoclingServeExtractor

    ProcessingManifest *-- SourceDocument
    ProcessingManifest *-- ExtractorRun
    ProcessingManifest *-- ManifestElement
    ProcessingManifest *-- Obligation
    ProcessingManifest *-- ManifestSummary

    DoclingManifestExtractor ..> DoclingExtraction
    DoclingServeExtractor ..> DoclingExtraction
```

## Physical Architecture

The physical architecture describes how the system is deployed, the infrastructure components, and communication paths.

### Deployment Diagram

```mermaid
graph TB
    subgraph "Developer Machine"
        CLI[acessilia-extract CLI]
        DEV_ENV[Python 3.11+]
    end

    subgraph "Docker Host - Production"
        subgraph "Container: acessilia-extractor"
            API_PROC[Structure Extractor Process]
            VOL_CONFIG[/app/config]
        end

        subgraph "Container: docling-serve"
            SERVE[docling-serve]
            VOL_MODELS[/root/.cache/docling]
        end

        VOL_DATA[Volume: ./var]
        VOL_DOCLING[Volume: docling-models]
    end

    subgraph "Docker Host - Dev/Validation"
        subgraph "Container: validator"
            VAL[validate_snapshots.py]
        end
        subgraph "Container: test"
            TEST[pytest]
        end
    end

    subgraph "External"
        GHCR[GitHub Container Registry]
        DATASET[acessilia-dataset<br/>Git Submodule]
    end

    CLI -->|HTTP :8000| API_PROC
    API_PROC -->|HTTP :5001| SERVE
    API_PROC --> VOL_DATA
    SERVE --> VOL_DOCLING

    VAL -->|HTTP :5001| SERVE
    VAL --> DATASET

    TEST --> API_PROC

    GHCR -->|docker pull| API_PROC
    GHCR -->|docker pull| SERVE
```

### Docker Build Architecture

```mermaid
graph LR
    subgraph "Dockerfile Stages"
        BASE[base<br/>python:3.11-slim]
        PROD[production ★]
        WITH_DOCLING[with-docling<br/>Legacy]
        PROD_DOCLING[production-docling]
        TEST_STAGE[test]
        VAL_STAGE[validate-snapshots]
    end

    BASE --> PROD
    BASE -.-> WITH_DOCLING
    BASE --> TEST_STAGE

    WITH_DOCLING --> PROD_DOCLING
    WITH_DOCLING --> VAL_STAGE
```

### Network Architecture

```mermaid
graph TB
    subgraph "Docker Network"
        subgraph "Service: acessilia-extractor"
            API[Port :8000]
        end

        subgraph "Service: docling-serve"
            SERVE[Port :5001]
        end
    end

    subgraph "External Access"
        INTERNET[Internet / LAN]
    end

    INTERNET -->|":8000"| API
    API -->|":5001"| SERVE
```

### Container Specifications

| Container | Base Image | Size | Port | Dependencies |
|---|---|---|---|---|
| `acessilia-extractor` (production) | python:3.11-slim | ~200 MB | 8000 | httpx, PyMuPDF, pydantic |
| `acessilia-extractor` (with-docling) | python:3.11-slim | ~3 GB | 8000 | + docling, torch, rapidocr |
| `docling-serve` | ghcr.io/docling-project/serve-cpu | ~3 GB | 5001 | docling, torch, rapidocr |
| `validator` | python:3.11-slim | ~200 MB | — | + httpx (uses docling-serve) |
| `test` | python:3.11-slim | ~200 MB | — | + pytest |

### Data Flow Diagram

```mermaid
graph LR
    subgraph "Input"
        DOC[Document<br/>PDF / DOCX / Image]
        CFG[Configuration<br/>--language, --no-ocr]
    end

    subgraph "Processing"
        EXT[Extraction Engine]
        SAN[Text Sanitizer]
        TBL[Table Normalizer]
        BLD[Manifest Builder]
        VAL[Schema Validator]
    end

    subgraph "Output"
        MAN[Processing Manifest<br/>JSON]
        ERR[Validation Errors<br/>stderr]
    end

    DOC --> EXT
    CFG --> EXT
    EXT --> SAN
    EXT --> TBL
    SAN --> BLD
    TBL --> BLD
    BLD --> VAL
    VAL --> MAN
    VAL --> ERR
```

### Technology Stack

| Layer | Technology | Version |
|---|---|---|
| **Language** | Python | >= 3.11 |
| **Data Models** | Pydantic | >= 2 |
| **Schema Validation** | jsonschema (Draft 2020-12) | — |
| **HTTP Client** | httpx | >= 0.28 |
| **PDF/Light Extraction** | PyMuPDF | — |
| **Full Extraction** | docling-serve (recommended) | latest |
| **Local Extraction** | Docling | >= 2 |
| **OCR** | RapidOCR | — |
| **ML Runtime** | PyTorch (CPU) | — |
| **Testing** | pytest | >= 7 |
| **Container Runtime** | Docker | — |
| **Orchestration** | Docker Compose | — |
| **Registry** | GitHub Container Registry | — |