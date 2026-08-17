"""Dockerfile para o Acessilia Structure Extractor.

Variantes de build:
  docker build --target production -t acessilia-extractor:latest .
  docker build --target production-serve -t acessilia-extractor:serve .
  docker build --target test -t acessilia-extractor:test .
"""

# === Estágio base: Python + runtime mínimo ===
FROM python:3.11-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Dependências de sistema mínimas
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 libglib2.0-0 poppler-utils \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml ./
COPY src/ ./src/

# Instala o pacote (sem docling)
RUN pip install --upgrade pip && pip install . && rm -rf ~/.cache

# === Estágio de produção: sem Docling ===
FROM base AS production
COPY . .
EXPOSE 8000
CMD ["acessilia-extract"]

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

# === Estágio de teste ===
FROM base AS test
RUN pip install ".[dev]" && rm -rf ~/.cache
COPY . .
CMD ["pytest", "tests/", "-v"]

# === Estágio slim: só httpx + PyMuPDF, aponta para docling-serve remoto ===
FROM production AS production-serve
ENV DOCLING_SERVE_URL="http://docling-serve:5001"
CMD ["sh", "-c", "acessilia-extract --docling-serve $DOCLING_SERVE_URL"]