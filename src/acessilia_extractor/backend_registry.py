"""Backend registry — mapeia nomes de backend para extratores e variáveis de ambiente.

Cada backend de extração é um microserviço acessado via REST.
O registro centraliza a descoberta e resolução dos backends disponíveis.

Para adicionar um novo backend:
    1. Crie uma classe extrator em extractors.py (ex: GrobidServeExtractor)
    2. Adicione a entrada no dicionário BACKENDS abaixo
    3. Adicione a URL no .env.example
    4. Crie um docker-compose em services/<nome>/
"""

from __future__ import annotations

from pathlib import Path
import os
from typing import TYPE_CHECKING

from dotenv import load_dotenv

if TYPE_CHECKING:
    from acessilia_extractor.extractors import BaseExtractor


# Carrega .env da raiz do projeto (se existir)
_env_path = Path(__file__).resolve().parents[2] / ".env"
load_dotenv(_env_path)


BACKENDS: dict[str, dict[str, str]] = {
    "docling": {
        "class": "DoclingServeExtractor",
        "env_var": "DOCLING_SERVE_URL",
        "default_url": "http://docling-serve:5001",
        "description": "Docling via REST (IBM document understanding)",
    },
    # ─── Exemplo para futuros backends ───
    # "grobid": {
    #     "class": "GrobidServeExtractor",
    #     "env_var": "GROBID_SERVE_URL",
    #     "default_url": "http://grobid-serve:5002",
    #     "description": "GROBID (TEI XML extraction for scholarly documents)",
    # },
    # "mineru": {
    #     "class": "MineruServeExtractor",
    #     "env_var": "MINERU_SERVE_URL",
    #     "default_url": "http://mineru-serve:5003",
    #     "description": "MinerU (PDF structure extraction)",
    # },
    # "nougat": {
    #     "class": "NougatServeExtractor",
    #     "env_var": "NOUGAT_SERVE_URL",
    #     "default_url": "http://nougat-serve:5004",
    #     "description": "Nougat (OCR for academic documents)",
    # },
    # "marker": {
    #     "class": "MarkerServeExtractor",
    #     "env_var": "MARKER_SERVE_URL",
    #     "default_url": "http://marker-serve:5005",
    #     "description": "Marker (PDF to markdown conversion)",
    # },
    # "pp-structure": {
    #     "class": "PPStructureServeExtractor",
    #     "env_var": "PP_STRUCTURE_SERVE_URL",
    #     "default_url": "http://pp-structure-serve:5006",
    #     "description": "PP-StructureV3 (PaddleOCR layout analysis)",
    # },
    # "paddle-ocr": {
    #     "class": "PaddleOCRServeExtractor",
    #     "env_var": "PADDLE_OCR_SERVE_URL",
    #     "default_url": "http://paddle-ocr-serve:5007",
    #     "description": "PaddleOCR (OCR engine)",
    # },
    # "surya": {
    #     "class": "SuryaServeExtractor",
    #     "env_var": "SURYA_SERVE_URL",
    #     "default_url": "http://surya-serve:5008",
    #     "description": "Surya (multilingual OCR and layout)",
    # },
}


def resolve_backend(backend_name: str | None = None) -> tuple[str, str]:
    """Resolve o backend e sua URL.

    A resolução segue a ordem:
    1. Argumento explícito ``backend_name``
    2. Variável de ambiente ``EXTRACTOR_BACKEND``
    3. ``"docling"`` (padrão)

    Retorna (backend_name, url).
    """
    name = backend_name or os.environ.get("EXTRACTOR_BACKEND") or "docling"

    entry = BACKENDS.get(name)
    if entry is None:
        valid = ", ".join(sorted(BACKENDS))
        raise ValueError(
            f"Backend desconhecido: '{name}'. "
            f"Backends disponíveis: {valid}"
        )

    url = os.environ.get(entry["env_var"]) or entry["default_url"]
    return name, url


def get_available_backends() -> list[dict[str, str]]:
    """Retorna lista de backends disponíveis com metadados."""
    return [
        {
            "name": name,
            "description": info["description"],
            "env_var": info["env_var"],
            "default_url": info["default_url"],
        }
        for name, info in sorted(BACKENDS.items())
    ]


def create_extractor(
    backend_name: str | None = None,
    base_url: str | None = None,
) -> BaseExtractor:
    """Cria e retorna uma instância do extrator para o backend indicado."""
    from acessilia_extractor.extractors import DoclingServeExtractor

    name, url = resolve_backend(backend_name)
    url = base_url or url

    if name == "docling":
        return DoclingServeExtractor(base_url=url)

    # Futuros backends serão adicionados aqui
    # if name == "grobid":
    #     from acessilia_extractor.extractors import GrobidServeExtractor
    #     return GrobidServeExtractor(base_url=url)

    raise ValueError(f"Backend '{name}' reconhecido mas sem implementação.")
