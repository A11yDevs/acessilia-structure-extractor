# Installation

## Prerequisites

- **Python** >= 3.11
- **pip** (up to date)
- **Docker** (required for docling-serve)
- **Git** (to clone the repository)

## Quick Start (Recommended)

The recommended setup uses **docling-serve** via Docker, avoiding the need to install PyTorch and Docling locally.

### 1. Clone the Repository

```bash
git clone https://github.com/A11yDevs/acessilia-structure-extractor.git
cd acessilia-structure-extractor
```

### 2. Install the Base Package

```bash
pip install --upgrade pip
pip install .
```

This installs only the minimum dependencies:

- `pydantic>=2` — data models
- `jsonschema` — schema validation
- `httpx>=0.28` — HTTP client (for docling-serve)
- `PyMuPDF` — lightweight extraction (planned)

### 3. Start docling-serve

```bash
docker pull ghcr.io/docling-project/docling-serve-cpu:v1.32.0
docker run -d \
  --name docling-serve \
  -p 5001:5001 \
  -v docling-models:/root/.cache/docling \
  ghcr.io/docling-project/docling-serve-cpu:v1.32.0
```

> **Note**: The first request will download Docling's ML models (~2 GB), which are cached in the `docling-models` volume for subsequent runs.

### 4. Configure Environment (Optional)

```bash
cp .env.example .env
# Edit .env to adjust DOCLING_SERVE_URL if needed
```

The `.env` file is loaded automatically by Docker Compose and read by the CLI.

### 5. Verify the Installation

```bash
# Check that docling-serve is healthy
curl http://localhost:5001/health

# Check that the CLI is available
acessilia-extract --help
```

### 6. Extract a Document

```bash
export DOCLING_SERVE_URL=http://localhost:5001
acessilia-extract documento.pdf
```

## Alternative: Local Docling Installation

If you prefer to run Docling locally (not recommended on macOS due to PyTorch compatibility issues):

```bash
pip install ".[docling]"
```

Additional dependencies:

- `docling>=2` — full extraction pipeline
- `torch` — PyTorch runtime (CPU)
- `rapidocr` — OCR for scanned documents

## Development Installation

```bash
pip install ".[dev]"
```

Adds:

- `pytest>=7`
- `pytest-asyncio`

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
# Start the main service with docling-serve
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
| `production` | ❌ | ~200 MB | **Default** — uses remote docling-serve |
| `with-docling` | ✅ | ~3 GB | Legacy — local Docling (not recommended) |
| `production-docling` | ✅ | ~3 GB | Production with embedded Docling |
| `test` | ❌ | ~200 MB | Unit tests |
| `validate-snapshots` | ✅ | ~3 GB | Snapshot validation |

### Docling Model Cache

Docling models are downloaded on first request and cached in a Docker volume:

```yaml
volumes:
  docling-models:  # /root/.cache/docling
```

For snapshot validation with docling-serve, use:

```bash
docker compose -f docker-compose.test-snapshot.yml up --build validator
```

## Using docling-serve

### 1. Pull the Image

```bash
docker pull ghcr.io/docling-project/docling-serve-cpu:v1.32.0
```

This downloads the CPU-optimized version (~3 GB). If you have an NVIDIA GPU, use:

```bash
docker pull ghcr.io/docling-project/docling-serve:latest
```

### 2. Start the Server

```bash
docker run -d \
  --name docling-serve \
  -p 5001:5001 \
  -v docling-models:/root/.cache/docling \
  ghcr.io/docling-project/docling-serve-cpu:v1.32.0
```

The server listens on `http://localhost:5001`.

### 3. Verify It's Running

```bash
curl http://localhost:5001/health
```

Expected response: `{"status":"ok"}`

### 4. Use with the Acessilia Extractor

Once docling-serve is running, use the extractor with the `--docling-serve` flag:

```bash
acessilia-extract --docling-serve http://localhost:5001 documento.pdf
```

Or set the environment variable:

```bash
export DOCLING_SERVE_URL=http://localhost:5001
acessilia-extract documento.pdf
```

### 5. Stop the Server

```bash
docker stop docling-serve
docker rm docling-serve
```

### Docker Compose (Integrated)

The project already includes a `docker-compose.test-snapshot.yml` that orchestrates both docling-serve and the validator:

```bash
docker compose -f docker-compose.test-snapshot.yml up --build validator
```

This starts docling-serve, waits for it to become healthy, then runs the snapshot validation suite against it.

## Configuration

### Environment Variables

The project supports configuration via a `.env` file (loaded automatically by Docker Compose and read by the CLI).

```bash
# Copy the example file and adjust as needed
cp .env.example .env
```

| Variable | Default | Description |
|---|---|---|
| `DOCLING_SERVE_URL` | `http://docling-serve:5001` | Remote docling-serve URL |
| `DOCLING_SERVE_ENABLE_UI` | `false` | Disable docling-serve web UI |
| `DOCLING_SERVE_IMAGE` | `ghcr.io/docling-project/docling-serve-cpu:v1.32.0` | Pinned docling-serve Docker image |
| `DOCLING_SERVE_PORT` | `5001` | Host port for docling-serve |

> **Note**: The `.env` file is gitignored. Use `.env.example` as a template for your local configuration.

### CLI

```bash
acessilia-extract [options] <document>

Arguments:
  document                 Input document (PDF, DOCX, image)

Options:
  -o, --output PATH        Output JSON (default: <document>.processing-manifest.json)
  --language LANG          BCP 47 language (default: pt-BR)
  --no-ocr                 Disable OCR in the PDF pipeline
  --docling-serve URL      Use remote docling-serve (default: $DOCLING_SERVE_URL)
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