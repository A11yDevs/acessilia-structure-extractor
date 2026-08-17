"""Testes de snapshot — valida que o extrator produz os mesmos resultados do Acessilia.

Requer docling-serve rodando em DOCLING_SERVE_URL (default: http://localhost:5001).

Para rodar:
    docker compose -f docker-compose.test-snapshot.yml up --build

Ou manualmente com docling-serve local:
    DOCLING_SERVE_URL=http://localhost:5001 pytest tests/test_snapshot.py -v
"""

from __future__ import annotations

import csv
import json
import os
from pathlib import Path

import pytest

from tests.conftest import DATASET_DIR, DOCUMENTS_DIR, EXPECTED_DIR
from tests.snapshot_comparator import compare_manifests


# URL do docling-serve (via env ou default)
DOCLING_SERVE_URL = os.getenv("DOCLING_SERVE_URL", "http://localhost:5001")

# Skip se não houver dataset
pytestmark = pytest.mark.skipif(
    not DATASET_DIR.exists(),
    reason=f"Dataset não encontrado em {DATASET_DIR}. "
           "Execute: git submodule update --init tests/dataset",
)


def _get_fixtures() -> list[tuple[str, Path, Path]]:
    """Retorna lista de (doc_id, document_path, expected_path)."""
    manifest_path = DATASET_DIR / "input" / "manifest.csv"
    fixtures: list[tuple[str, Path, Path]] = []

    if manifest_path.exists():
        with open(manifest_path) as f:
            reader = csv.DictReader(f)
            for row in reader:
                doc_id = row["id"]
                expected_path = EXPECTED_DIR / f"{doc_id}.json"
                if not expected_path.exists():
                    continue

                # Procura o documento
                filename = row["original_filename"]
                doc_path = DOCUMENTS_DIR / filename
                if not doc_path.exists():
                    # Tenta por id + extensão
                    for ext in (".pdf", ".jpeg", ".jpg", ".png"):
                        p = DOCUMENTS_DIR / f"{doc_id}{ext}"
                        if p.exists():
                            doc_path = p
                            break

                if doc_path.exists():
                    fixtures.append((doc_id, doc_path, expected_path))
    else:
        # Fallback: lista diretório
        for doc_path in sorted(DOCUMENTS_DIR.glob("*")):
            if doc_path.is_dir() or doc_path.suffix == ".csv":
                continue
            doc_id = doc_path.stem
            expected_path = EXPECTED_DIR / f"{doc_id}.json"
            if expected_path.exists():
                fixtures.append((doc_id, doc_path, expected_path))

    return fixtures


def _get_extractor():
    """Cria o extrator docling-serve (import lazy para evitar erro sem httpx)."""
    from acessilia_extractor.extractors import DoclingServeExtractor
    return DoclingServeExtractor(base_url=DOCLING_SERVE_URL)


def _extract_document(doc_path: Path, language: str = "pt-BR"):
    """Extrai documento e retorna o manifesto como dict."""
    from acessilia_extractor.manifest.builder import build_processing_manifest
    extractor = _get_extractor()
    extraction = extractor.extract(doc_path)
    manifest = build_processing_manifest(doc_path, extraction, language=language)
    return manifest.model_dump(mode="json", by_alias=True)


# Fixtures parametrizadas
FIXTURES = _get_fixtures()


@pytest.mark.skipif(
    not FIXTURES,
    reason="Nenhum documento com expected encontrado no dataset",
)
@pytest.mark.parametrize(
    "doc_id,doc_path,expected_path",
    FIXTURES,
    ids=[f[0] for f in FIXTURES],
)
def test_snapshot_processing_manifest(doc_id, doc_path, expected_path, tmp_path):
    """Extrai o documento e compara com o expected snapshot."""
    try:
        actual = _extract_document(doc_path)
    except Exception as e:
        pytest.fail(f"Falha na extração de {doc_path.name}: {e}")

    # Salva o resultado atual para debug
    actual_path = tmp_path / f"{doc_id}.actual.json"
    with open(actual_path, "w") as f:
        json.dump(actual, f, indent=2, ensure_ascii=False)

    # Compara
    diffs = compare_manifests(expected_path, actual_path)

    if diffs:
        # Salva snapshot para análise
        snapshot_dir = tmp_path.parent / "snapshots"
        snapshot_dir.mkdir(parents=True, exist_ok=True)
        snapshot_path = snapshot_dir / f"{doc_id}.actual.json"
        import shutil
        shutil.copy(actual_path, snapshot_path)
        pytest.fail(
            f"Snapshot divergiu para {doc_path.name} (doc {doc_id}):\n"
            + "\n".join(diffs)
            + f"\nResultado atual salvo em: {snapshot_path}"
        )


def test_expected_files_exist():
    """Verifica se todo documento tem expected correspondente."""
    manifest_path = DATASET_DIR / "input" / "manifest.csv"
    if not manifest_path.exists():
        pytest.skip("Sem manifest.csv")

    missing = []
    with open(manifest_path) as f:
        reader = csv.DictReader(f)
        for row in reader:
            doc_id = row["id"]
            expected = EXPECTED_DIR / f"{doc_id}.json"
            if not expected.exists():
                missing.append(f"{doc_id} ({row['original_filename']})")

    if missing:
        pytest.fail(f"Expected outputs faltando para: {', '.join(missing)}")