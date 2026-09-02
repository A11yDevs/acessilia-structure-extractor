# Extraction Tools

## Overview

The Acessilia Structure Extractor supports multiple document extraction backends, each with its own characteristics. The abstract `BaseExtractor` interface allows switching between them without modifying the manifest building pipeline.

## Docling

[Docling](https://github.com/docling-project/docling) is the document understanding engine developed by IBM. It provides deep structural understanding of documents and is used indirectly via **docling-serve** (recommended) or directly as a local library.

### Features

| Feature | Support |
|---|---|
| **Input formats** | PDF, DOCX, XLSX, PPTX, HTML, images |
| **OCR** | ✅ (RapidOCR, Tesseract) |
| **Table structure** | ✅ (specialized model) |
| **Heading hierarchy** | ✅ |
| **Reading order** | ✅ |
| **Figures and images** | ✅ |
| **Formulas** | ✅ |
| **Lists** | ✅ |
| **Footnotes** | ✅ |
| **Headers/footers** | ✅ |
| **ML models** | ✅ (downloaded at runtime) |
| **Languages** | Multilingual (OCR + layout) |

### Docling Architecture

```mermaid
graph LR
    PDF[PDF] --> Parser[Parser]
    Parser --> Layout[Layout Analysis]
    Layout --> OCR[OCR / RapidOCR]
    Layout --> Table[Table Structure]
    Layout --> Reading[Reading Order]
    OCR --> DoclingDoc[DoclingDocument]
    Table --> DoclingDoc
    Reading --> DoclingDoc
```

### Usage in the Project

Docling is used in two ways:

1. **Remote (recommended)** — `DoclingServeExtractor`: via `docling-serve`, REST communication. No local ML dependencies required.
2. **Local** — `DoclingManifestExtractor`: installed in the same environment, loads models at runtime. Requires the `[docling]` extra.

### Dependencies

```toml
[project.optional-dependencies]
docling = [
    "docling>=2",
]
```

### Model Cache

Models are downloaded automatically on first request:

- **Docker volume**: `docling-models` (mounted at `/root/.cache/docling`)
- **Local**: `~/.cache/huggingface` and `~/.cache/docling`

> ⚠️ The first request is significantly slower due to model downloads.

## docling-serve (Recommended)

[docling-serve](https://github.com/docling-project/docling-serve) is the REST server that exposes Docling as a service. It is the **recommended** way to use Docling with the Acessilia Structure Extractor, as it avoids installing PyTorch and heavy ML dependencies locally.

### Features

| Feature | Support |
|---|---|
| **REST API** | ✅ (v1) |
| **Multipart upload** | ✅ |
| **JSON output** | ✅ (serialized DoclingDocument) |
| **Processing queue** | ✅ |
| **Health check** | ✅ (`/health`) |
| **Multiple formats** | ✅ (json, text, markdown) |
| **GPU** | ✅ (`docling-serve` image) |
| **CPU** | ✅ (`docling-serve-cpu` image) |

### Usage with Docker

```bash
# Start docling-serve
docker run -p 5001:5001 \
  -v docling-models:/root/.cache/docling \
  ghcr.io/docling-project/docling-serve-cpu:v1.32.0

# Extract via API
curl -X POST http://localhost:5001/v1/convert/file \
  -F "files=@document.pdf" \
  -F "to_formats=[\"json\"]"
```

### Integration

The `DoclingServeExtractor` sends the document via multipart upload and receives the JSON content. A wrapper (`_BuildDoclingDocument`) converts the response to the interface expected by the builder.

```python
from acessilia_extractor.extractors import DoclingServeExtractor

extractor = DoclingServeExtractor(base_url="http://docling-serve:5001")
extraction = extractor.extract(Path("document.pdf"))
```

## PyMuPDF (fitz)

[PyMuPDF](https://pymupdf.readthedocs.io/) is a lightweight alternative for basic extraction.

### Features

| Feature | Support |
|---|---|
| **Formats** | PDF, images |
| **OCR** | ❌ (not native) |
| **Text** | ✅ |
| **Tables** | ⚠️ (basic) |
| **Images** | ✅ |
| **Metadata** | ✅ |
| **Annotations** | ✅ |
| **Dependencies** | Minimal (no ML) |

### Project Status

PyMuPDF is listed as a base dependency and is planned as an alternative backend for lightweight extraction without ML models. There is currently no `PyMuPDFExtractor` implemented — the `BaseExtractor` interface is ready to receive it.

### Planned Use Cases

- Fast text extraction without heavy dependencies
- Fallback when Docling is unavailable
- Metadata and annotation extraction
- Pre-processing for structure validation

## Comparison

| Criteria | docling-serve ★ | Docling | PyMuPDF |
|---|---|---|---|---|
| **Structural accuracy** | High | High | Medium |
| **Speed** | Slow + network latency | Slow (models) | Fast |
| **Image size** | ~3 GB (server) | ~3 GB | ~200 MB |
| **OCR** | ✅ | ✅ | ❌ |
| **Tables** | ✅ | ✅ | ⚠️ |
| **ML models** | ✅ (server-side) | ✅ | ❌ |
| **Offline use** | ✅ (after cache) | ✅ (after cache) | ✅ |
| **Local ML deps** | ❌ (no PyTorch) | ✅ (PyTorch) | ❌ |
| **Recommended for** | **Default — maximum accuracy without local ML** | Maximum accuracy (legacy) | Fast extraction |

## Post-processing Pipeline

Regardless of the backend, the post-processing pipeline includes:

### Sanitization (`pipeline/sanitizer.py`)

- Removes control characters
- Removes prompt leaks (patterns like "chain of thought", "ignore previous instructions")
- Removes Markdown artifacts (headings, lists, bold/italic)
- Removes audio description metadata

### Table Normalization (`pipeline/table_ast.py`)

- Converts varied table representations into a canonical AST
- Supports header/body/footer sections
- Preserves captions and metadata
- Enables linearization for sequential reading