# Dockerfile para o Acessilia Structure Extractor
#
# Uso recomendado:
#   docker compose up -d                    # Sobe com docling-serve
#
# Build manual:
#   docker build --target production -t acessilia-extractor:latest .
#   docker build --target with-docling -t acessilia-extractor:with-docling .
#   docker build --target validate-snapshots -t acessilia-extractor:validate .

FROM python:3.11-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Dependências de sistema mínimas (necessárias para PyMuPDF)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 libglib2.0-0 poppler-utils \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml ./
COPY src/ ./src/

# Instala o pacote base (sem docling)
RUN pip install --upgrade pip && pip install . && rm -rf ~/.cache

# === Estágio de produção: usa docling-serve remoto (padrão) ===
FROM base AS production
COPY . .
EXPOSE 8000
ENV DOCLING_SERVE_URL="http://docling-serve:5001"
CMD ["acessilia-extract"]

# === Estágio com Docling local (legado) ===
FROM base AS with-docling

# Dependências extras do docling/pytorch/rapidocr
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg libmagic1 tesseract-ocr \
    && rm -rf /var/lib/apt/lists/*

# Reinstala com o extra docling
RUN pip install --upgrade pip && pip install ".[docling]" && rm -rf ~/.cache

COPY . .

# === Estágio de validação de snapshots (usa docling local) ===
FROM with-docling AS validate-snapshots
ENTRYPOINT ["python3", "scripts/validate_snapshots.py"]
CMD ["--help"]

# === Estágio de teste ===
FROM base AS test
RUN pip install ".[dev]" && rm -rf ~/.cache
COPY . .
CMD ["pytest", "tests/", "-v"]

# === Estágio com Docling embutido (imagem maior) ===
FROM base AS docling

# Instala dependências extras do sistema (pytorch CPU, rapidocr)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg libmagic1 tesseract-ocr \
    && rm -rf /var/lib/apt/lists/*

# Reinstala com o extra docling
RUN pip install ".[docling]" && rm -rf ~/.cache

FROM docling AS production-docling
COPY . .
EXPOSE 8000
CMD ["acessilia-extract"]