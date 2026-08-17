"""CLI de extração de estrutura de documentos.

Uso:
    acessilia-extract document.pdf -o output.json
    acessilia-extract document.pdf --docling-serve http://localhost:5001
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from acessilia_extractor.extractors import (
    DoclingManifestExtractor,
    DoclingServeExtractor,
)
from acessilia_extractor.manifest.builder import build_processing_manifest
from acessilia_extractor.manifest.schema import validate_manifest


PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_SCHEMA = PROJECT_ROOT / "schemas" / "processing_manifest.schema.json"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="acessilia-extract",
        description=(
            "Extrai a estrutura de um documento e gera um "
            "manifesto de processamento validado."
        ),
    )
    parser.add_argument("document", type=Path, help="Documento de entrada (PDF, DOCX, imagem).")
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        help="JSON de saída (padrão: <documento>.processing-manifest.json).",
    )
    parser.add_argument(
        "--language",
        default="pt-BR",
        help="Idioma BCP 47 assumido para o documento (padrão: pt-BR).",
    )
    parser.add_argument(
        "--no-ocr",
        action="store_true",
        help="Desabilita OCR no pipeline PDF do Docling (modo local apenas).",
    )
    parser.add_argument(
        "--docling-serve",
        type=str,
        default=None,
        metavar="URL",
        help=(
            "Usa docling-serve remoto em vez de Docling embutido. "
            "Ex: http://localhost:5001"
        ),
    )
    parser.add_argument(
        "--schema",
        type=Path,
        default=DEFAULT_SCHEMA if DEFAULT_SCHEMA.exists() else None,
        help="Schema usado na validação Draft 2020-12.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    source = args.document.resolve()
    output = (
        args.output.resolve()
        if args.output
        else source.with_suffix(".processing-manifest.json")
    )

    try:
        # Seleciona o backend de extração
        if args.docling_serve:
            extractor = DoclingServeExtractor(base_url=args.docling_serve)
        else:
            extractor = DoclingManifestExtractor(enable_ocr=not args.no_ocr)

        extraction = extractor.extract(source)
        manifest = build_processing_manifest(
            source,
            extraction,
            language=args.language,
        )
        payload = manifest.model_dump(mode="json", by_alias=True)

        if args.schema and args.schema.exists():
            errors = validate_manifest(payload, args.schema.resolve())
            if errors:
                print("Manifesto inválido:", file=sys.stderr)
                for error in errors:
                    print(f"- {error}", file=sys.stderr)
                return 2

        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

        print(f"Manifesto válido: {output}")
        print(
            f"Páginas: {manifest.summary.page_count}; "
            f"elementos: {manifest.summary.element_count}; "
            f"obrigações candidatas: {manifest.summary.obligation_count}"
        )
        return 0

    except Exception as exc:
        print(f"Erro: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())