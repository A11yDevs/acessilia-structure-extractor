#!/usr/bin/env python3
"""Script de validação de snapshot — extrai documentos e compara com expected.

Uso com Docling local (recomendado via Docker):
    docker compose -f docker-compose.test-snapshot.yml up --build validator

Uso com docling-serve remoto:
    python scripts/validate_snapshots.py --backend serve --docling-serve http://localhost:5001

Uso para atualizar expected outputs:
    python scripts/validate_snapshots.py --update
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
import time
from pathlib import Path

# Permite importar o pacote mesmo sem instalação
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tests"))

from acessilia_extractor.manifest.builder import build_processing_manifest
from snapshot_comparator import compare_manifests


DATASET_DIR = Path(__file__).resolve().parents[1] / "tests" / "dataset"
DOCUMENTS_DIR = DATASET_DIR / "input"
EXPECTED_DIR = DATASET_DIR / "intermediate" / "processing-manifest"
OUTPUT_DIR = Path(__file__).resolve().parents[1] / "tests" / "snapshots"


def get_fixtures() -> list[tuple[str, Path]]:
    """Retorna lista de (doc_id, document_path) do dataset, seguindo o manifest.csv.
    Pula documentos com mais de 40 páginas (muito extensos para processamento local)."""
    manifest_path = DATASET_DIR / "input" / "manifest.csv"
    fixtures: list[tuple[str, Path]] = []
    max_pages = 40

    if manifest_path.exists():
        with open(manifest_path) as f:
            reader = csv.DictReader(f)
            for row in reader:
                doc_id = row["id"]
                pages = int(row.get("pages", 0))
                if pages > max_pages:
                    print(f"  ⏭️  {doc_id} ({row['original_filename']}) — {pages}pgs, pulando (>40)")
                    continue
                filename = row["original_filename"]
                doc_path = DOCUMENTS_DIR / filename
                if doc_path.exists():
                    fixtures.append((doc_id, doc_path))
                else:
                    for ext in (".pdf", ".jpeg", ".jpg", ".png"):
                        p = DOCUMENTS_DIR / f"{doc_id}{ext}"
                        if p.exists():
                            fixtures.append((doc_id, p))
                            break
    else:
        for p in sorted(DOCUMENTS_DIR.glob("*.pdf")):
            fixtures.append((p.stem, p))

    return fixtures


def create_extractor(backend: str, serve_url: str | None):
    """Cria o extrator apropriado."""
    if backend == "serve":
        if not serve_url:
            serve_url = "http://localhost:5001"
        from acessilia_extractor.extractors import DoclingServeExtractor
        return DoclingServeExtractor(base_url=serve_url)
    else:
        from acessilia_extractor.extractors import DoclingManifestExtractor
        return DoclingManifestExtractor(enable_ocr=True)


def main() -> int:
    parser = argparse.ArgumentParser(description="Valida snapshots de extração")
    parser.add_argument(
        "--backend",
        choices=["local", "serve"],
        default="local",
        help="Backend de extração: local (Docling) ou serve (docling-serve)",
    )
    parser.add_argument(
        "--docling-serve",
        default=None,
        help="URL do docling-serve (usado apenas com --backend serve)",
    )
    parser.add_argument(
        "--language",
        default="pt-BR",
        help="Idioma BCP 47",
    )
    parser.add_argument(
        "--wait",
        type=int,
        default=0,
        help="Segundos para aguardar antes de começar",
    )
    parser.add_argument(
        "--update",
        action="store_true",
        help="Atualiza os expected outputs com os resultados obtidos",
    )
    args = parser.parse_args()

    if args.wait:
        print(f"Aguardando {args.wait}s...")
        time.sleep(args.wait)

    extractor = create_extractor(args.backend, args.docling_serve)
    fixtures = get_fixtures()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    passed = 0
    failed = 0
    skipped = 0
    updated = 0

    backend_name = "docling" if args.backend == "local" else "docling-serve"
    print(f"Dataset: {DATASET_DIR}")
    print(f"Documentos: {len(fixtures)}")
    print(f"Backend: {backend_name}")
    if args.update:
        print("Modo: ATUALIZAR expected outputs")
    print()

    for doc_id, fixture in fixtures:
        expected_path = EXPECTED_DIR / f"{doc_id}.json"

        if not expected_path.exists() and not args.update:
            print(f"  ⏭️  {fixture.name} (doc {doc_id}) — sem expected")
            skipped += 1
            continue

        print(f"  🔄 {fixture.name} (doc {doc_id})...", end=" ", flush=True)

        try:
            extraction = extractor.extract(fixture)
            manifest = build_processing_manifest(
                fixture, extraction, language=args.language,
            )
            actual = manifest.model_dump(mode="json", by_alias=True)

            # Salva resultado atual
            actual_path = OUTPUT_DIR / f"{doc_id}.actual.json"
            with open(actual_path, "w") as f:
                json.dump(actual, f, indent=2, ensure_ascii=False)

            if args.update:
                # Atualiza o expected
                with open(expected_path, "w") as f:
                    json.dump(actual, f, indent=2, ensure_ascii=False)
                print("✅ ATUALIZADO")
                updated += 1
                continue

            # Compara com o expected
            diffs = compare_manifests(expected_path, actual_path)

            if not diffs:
                print("✅ OK")
                passed += 1
            else:
                print("❌ DIFERENTE")
                for d in diffs:
                    print(f"       - {d}")
                failed += 1

        except Exception as e:
            print(f"💥 ERRO: {e}")
            import traceback
            traceback.print_exc()
            failed += 1

    print()
    if args.update:
        print(f"Resultado: {updated} snapshots atualizados")
    else:
        print(f"Resultado: {passed} passaram, {failed} falharam, {skipped} pularam")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())