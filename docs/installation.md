# Installation

## Prerequisites

- **Python** >= 3.11
- **pip** (up to date)
- **Docker** (optional, for containerized deployment)
- **Git** (to clone the repository)

## Local Installation

### 1. Clone the Repository

```bash
git clone https://github.com/A11yDevs/acessilia-structure-extractor.git
cd acessilia-structure-extractor
```

### 2. Install the Base Package (without Docling)

```bash
pip install --upgrade pip
pip install .
```

This installs the minimum dependencies:

- `pydantic>=2` — data models
- `jsonschema` — schema validation
- `httpx>=0.28` — HTTP client (for docling-serve)
- `PyMuPDF` — lightweight extraction (planned)

### 3. Install with Docling Support

```bash
pip install ".[docling]"
```

Additional dependencies:

- `docling>=2` — full extraction pipeline
- `torch` — PyTorch runtime (CPU)
- `rapidocr` — OCR for scanned documents

### 4. Install with Development Dependencies

```bash
pip install ".[dev]"
```

Adds:

- `pytest>=7`
- `pytest-asyncio`

### 5. Verify the Installation

```bash
acessilia-extract --help
```

## Docker

### Pre-built Images

CI publishes images to GitHub Container Registry:

```bash
# With Docling (full image)
docker pull ghcr.io/a11ydevs/acessilia-structure-extractor:main

# Without Docling (slim image)
docker pull ghcr.io/a11ydevs/acessilia-structure-extractor:main-slim
```

### Local Build

```bash
# Production image (without Docling)
docker build --target production -t acessilia-extractor:latest .

# Image with Docling
docker build --target with-docling -t acessilia-extractor:with-docling .

# Snapshot validation image
docker build --target validate-snapshots -t acessilia-extractor:validate .

# Test image
docker build --target test -t acessilia-extractor:test .
```

### Docker Compose

```bash
# Start the main service with Docling
docker compose up -d

# Run tests
docker compose run --rm test

# Validate snapshots
docker compose run --rm validate
```

### Deploy Variants

The `Dockerfile` offers multiple targets for different scenarios:

| Target | Docling | Size | Use Case |
|---|---|---|---|
| `production` | ❌ | ~200 MB | Production — uses remote docling-serve |
| `with-docling` | ✅ | ~3 GB | Development and validation |
| `production-docling` | ✅ | ~3 GB | Production with embedded Docling |
| `production-serve` | ❌ | ~200 MB | Points to external docling-serve |
| `test` | ❌ | ~200 MB | Unit tests |
| `validate-snapshots` | ✅ | ~3 GB | Snapshot validation |

### Docling Model Cache

Docling models are downloaded on first run and cached in a Docker volume:

```yaml
volumes:
  docling-models:  # /root/.cache/docling
```

For production with remote docling-serve, use:

```bash
docker compose -f docker-compose.test-snapshot.yml up --build validator
```

## Configuration

### Environment Variables

| Variable | Default | Description |
|---|---|---|
| `DOCLING_SERVE_URL` | `http://docling-serve:5001` | Remote docling-serve URL |

### CLI

```bash
acessilia-extract [options] <document>

Arguments:
  document                 Input document (PDF, DOCX, image)

Options:
  -o, --output PATH        Output JSON (default: <document>.processing-manifest.json)
  --language LANG          BCP 47 language (default: pt-BR)
  --no-ocr                 Disable OCR in the PDF pipeline
  --docling-serve URL      Use remote docling-serve instead of local Docling
  --schema PATH            Schema for Draft 2020-12 validation
```

## Tests

### Unit Tests

```bash
pytest tests/ -v
```

### Snapshots (requires docling-serve)

```bash
# Via Docker
docker compose -f docker-compose.test-snapshot.yml up --build

# Or manually
DOCLING_SERVE_URL=http://localhost:5001 pytest tests/test_snapshot.py -v
```

### Update Snapshots

```bash
python scripts/validate_snapshots.py --update
```

## Integration with the Central Project

The Acessilia Structure Extractor is consumed by [Acessilia](https://github.com/A11yDevs/acessilia) as an external service. The central project configuration must point to the extractor URL:

```env
# Acessilia .env
STRUCTURE_EXTRACTOR_URL=http://acessilia-extractor:8000
```