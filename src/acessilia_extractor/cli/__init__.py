"""CLI de extração de estrutura de documentos.

Uso:
    acessilia-extract documento.pdf -o output.json
    acessilia-extract documento.pdf --backend docling
    acessilia-extract documento.pdf --backend docling --docling-serve http://localhost:5001

O backend padrão é "docling" (docling-serve via Docker).
A URL do backend pode ser configurada via variável de ambiente
(ver .env.example) ou via flag --<backend>-serve.

O arquivo .env na raiz do projeto é carregado automaticamente.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from dotenv import load_dotenv

from acessilia_extractor.backend_registry import (
    create_extractor,
    get_available_backends,
    resolve_backend,
)
from acessilia_extractor.manifest.builder import build_processing_manifest
from acessilia_extractor.manifest.schema import validate_manifest


PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_SCHEMA = PROJECT_ROOT / "schemas" / "processing_manifest.schema.json"

# Carrega .env da raiz do projeto (se existir)
load_dotenv(PROJECT_ROOT / ".env")


def build_parser() -> argparse.ArgumentParser:
    backends = get_available_backends()
    backend_names = [b["name"] for b in backends]
    default_backend = backend_names[0] if backend_names else "docling"

    parser = argparse.ArgumentParser(
        prog="acessilia-extract",
        description=(
            "Extrai a estrutura de um documento e gera um "
            "manifesto de processamento validado."
        ),
    )
    parser.add_argument(
        "document",
        nargs="?",
        type=Path,
        help="Documento de entrada (PDF, DOCX, imagem).",
    )
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
        "--backend",
        type=str,
        default=None,
        choices=backend_names,
        help=(
            "Backend de extração (padrão: lido de EXTRACTOR_BACKEND env "
            f"ou {default_backend})."
        ),
    )
    parser.add_argument(
        "--list-backends",
        action="store_true",
        help="Lista os backends disponíveis e sai.",
    )
    # Gera flags --<backend>-serve para cada backend
    for backend in backends:
        flag = f"--{backend['name'].replace('_', '-')}-serve"
        env_var = backend["env_var"]
        parser.add_argument(
            flag,
            type=str,
            default=None,
            metavar="URL",
            help=f"URL do servidor {backend['name']} (padrão: ${env_var}).",
        )
    parser.add_argument(
        "--schema",
        type=Path,
        default=DEFAULT_SCHEMA if DEFAULT_SCHEMA.exists() else None,
        help="Schema usado na validação Draft 2020-12.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    # Lista backends e sai
    if args.list_backends:
        backends = get_available_backends()
        print("Backends disponíveis:")
        for b in backends:
            print(f"  {b['name']:20s}  {b['description']}")
            print(f"  {'':20s}  env: {b['env_var']}")
            print(f"  {'':20s}  url: {b['default_url']}")
            print()
        return 0

    if args.document is None:
        parser.error("o argumento document é obrigatório, exceto com --list-backends")

    source = args.document.resolve()
    output = (
        args.output.resolve()
        if args.output
        else source.with_suffix(".processing-manifest.json")
    )

    try:
        # Resolve backend e URL:
        # 1. --backend flag
        # 2. EXTRACTOR_BACKEND env var
        # 3. Flag --<backend>-serve (sobrescreve URL)
        # 4. Variável de ambiente <BACKEND>_SERVE_URL
        # 5. URL padrão do registro
        backend_name, backend_url = resolve_backend(args.backend)

        # Verifica se há flag --<backend>-serve para sobrescrever a URL
        flag_name = f"{backend_name.replace('-', '_')}_serve"
        flag_url = getattr(args, flag_name, None)
        if flag_url:
            backend_url = flag_url

        extractor = create_extractor(backend_name, base_url=backend_url)

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