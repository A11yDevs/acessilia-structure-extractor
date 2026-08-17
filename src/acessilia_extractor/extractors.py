"""Extraction backends — base interface and implementations."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter
from typing import Any


@dataclass(frozen=True)
class DoclingExtraction:
    """Resultado normalizado de uma extração Docling."""
    document: Any
    started_at: datetime
    completed_at: datetime
    duration_ms: int
    version: str
    configuration: dict[str, Any]


class BaseExtractor(ABC):
    """Interface comum para extratores de documentos."""

    @abstractmethod
    def extract(self, source_path: Path) -> DoclingExtraction:
        """Extrai a estrutura de um documento."""
        ...


class DoclingManifestExtractor(BaseExtractor):
    """Extrator local usando Docling instalado no mesmo ambiente.

    Requer o extra ``[docling]`` instalado:
        pip install acessilia-structure-extractor[docling]
    """

    def __init__(
        self,
        *,
        enable_ocr: bool = True,
        structurer: Any = None,
    ) -> None:
        self.enable_ocr = enable_ocr
        self._structurer = structurer

    def extract(self, source_path: Path) -> DoclingExtraction:
        source_path = source_path.resolve()
        if not source_path.is_file():
            raise FileNotFoundError(f"Documento não encontrado: {source_path}")

        if self._structurer is None:
            converter = self._create_converter()
        else:
            converter = self._structurer

        started_at = datetime.now(timezone.utc)
        started_clock = perf_counter()
        document = self._convert_document(converter, source_path)
        duration_ms = round((perf_counter() - started_clock) * 1000)
        completed_at = datetime.now(timezone.utc)

        return DoclingExtraction(
            document=document,
            started_at=started_at,
            completed_at=completed_at,
            duration_ms=duration_ms,
            version=_package_version("docling"),
            configuration={
                "ocr": self.enable_ocr,
                "table_structure": True,
                "remote_services": False,
            },
        )

    def _create_converter(self) -> Any:
        try:
            from docling.document_converter import DocumentConverter
        except ImportError:
            raise RuntimeError(
                "Docling não está instalado. "
                "Execute: pip install 'acessilia-structure-extractor[docling]'"
            )

        from docling.datamodel.base_models import InputFormat
        from docling.datamodel.pipeline_options import (
            PdfPipelineOptions,
            RapidOcrOptions,
        )
        from docling.document_converter import PdfFormatOption

        pdf_options = PdfPipelineOptions()
        pdf_options.do_ocr = self.enable_ocr
        pdf_options.do_table_structure = True
        pdf_options.ocr_options = RapidOcrOptions(backend="torch")
        if hasattr(pdf_options, "enable_remote_services"):
            pdf_options.enable_remote_services = False
        return DocumentConverter(
            format_options={
                InputFormat.PDF: PdfFormatOption(pipeline_options=pdf_options),
            }
        )

    @staticmethod
    def _convert_document(converter: Any, source_path: Path) -> Any:
        if hasattr(converter, "convert"):
            result = converter.convert(str(source_path))
            return result.document
        if hasattr(converter, "_process_document"):
            return converter._process_document(source_path)
        raise RuntimeError(
            "Conversor incompatível: esperado convert() ou _process_document()."
        )


class DoclingServeExtractor(BaseExtractor):
    """Extrator remoto via docling-serve (API REST).

    O docling-serve deve estar rodando em um host acessível.
    Docker recomendado:

        docker run -p 5001:5001 -v docling-models:/models \\
            ghcr.io/docling/docling-serve:latest
    """

    def __init__(self, base_url: str = "http://docling-serve:5001"):
        self.base_url = base_url.rstrip("/")

    def extract(self, source_path: Path) -> DoclingExtraction:
        import httpx

        source_path = source_path.resolve()
        if not source_path.is_file():
            raise FileNotFoundError(f"Documento não encontrado: {source_path}")

        started_at = datetime.now(timezone.utc)
        started_clock = perf_counter()

        with httpx.Client(base_url=self.base_url, timeout=300) as client:
            # 1. Upload do documento
            with source_path.open("rb") as f:
                upload_resp = client.post(
                    "/v1/convert/document",
                    files={"document": (source_path.name, f, "application/pdf")},
                )
            upload_resp.raise_for_status()
            result = upload_resp.json()

            docling_doc = result.get("document") or result

        duration_ms = round((perf_counter() - started_clock) * 1000)
        completed_at = datetime.now(timezone.utc)

        return DoclingExtraction(
            document=_BuildDoclingDocument(docling_doc),
            started_at=started_at,
            completed_at=completed_at,
            duration_ms=duration_ms,
            version=_extract_serve_version(result, client),
            configuration={
                "extractor": "docling-serve",
                "base_url": self.base_url,
            },
        )


class _BuildDoclingDocument:
    """Wrapper para compatibilizar a resposta JSON do docling-serve
    com a interface esperada pelo builder (iterate_items, pages, num_pages)."""

    def __init__(self, payload: dict[str, Any]) -> None:
        self._payload = payload
        self._items: list[tuple[Any, int]] = []
        self._build_items()

    def _build_items(self) -> None:
        items: list[dict] = self._payload.get("items") or []
        for idx, item in enumerate(items):
            self._items.append((_ItemProxy(item), item.get("tree_level", 1)))

    def iterate_items(self, **kwargs: Any) -> Any:
        return iter(self._items)

    def num_pages(self) -> int:
        pages = self._payload.get("pages") or []
        return len(pages)

    @property
    def pages(self) -> dict[int, Any]:
        return {
            p["page_number"]: _PageProxy(p)
            for p in (self._payload.get("pages") or [])
        }


class _ItemProxy:
    """Proxy para itens individuais do documento."""

    def __init__(self, data: dict[str, Any]) -> None:
        self._data = data

    def __getattr__(self, name: str) -> Any:
        if name == "label":
            return _LabelProxy(self._data.get("label", "unknown"))
        if name == "prov":
            return [_ProvProxy(p) for p in (self._data.get("prov") or [])]
        if name == "parent":
            parent = self._data.get("parent")
            if parent:
                return _CrefProxy(parent)
            return None
        if name == "self_ref":
            return self._data.get("self_ref")
        if name in ("level", "confidence", "score"):
            return self._data.get(name)
        if name in ("text", "orig", "name", "marker", "enumerated", "content_layer"):
            return self._data.get(name)
        if name == "table":
            return self._data.get("table") or self._data.get("table_ast")
        for candidate in ("rows", "table_ast", "cells"):
            val = self._data.get(candidate)
            if val is not None:
                return val
        return None

    def model_dump(self, **kwargs: Any) -> dict[str, Any]:
        return self._data


class _LabelProxy:
    def __init__(self, value: str):
        self.value = value


class _ProvProxy:
    def __init__(self, data: dict) -> None:
        self.page_no = data.get("page_no") or data.get("page_number", 1)
        bbox_data = data.get("bbox")
        self.bbox = _BboxProxy(bbox_data) if bbox_data else None
        charspan = data.get("charspan")
        if isinstance(charspan, (list, tuple)) and len(charspan) == 2:
            self.charspan = (int(charspan[0]), int(charspan[1]))
        else:
            self.charspan = None


class _BboxProxy:
    def __init__(self, data: dict) -> None:
        self.l = data.get("left") or data.get("l", 0)
        self.t = data.get("top") or data.get("t", 0)
        self.r = data.get("right") or data.get("r", 0)
        self.b = data.get("bottom") or data.get("b", 0)
        origin = data.get("coord_origin", "TOPLEFT")
        self.coord_origin = _LabelProxy(origin)


class _CrefProxy:
    def __init__(self, data: dict) -> None:
        self.cref = data.get("$ref") or data.get("cref", "")


class _PageProxy:
    def __init__(self, data: dict) -> None:
        self.size = _SizeProxy(data.get("size") or data)


class _SizeProxy:
    def __init__(self, data: dict) -> None:
        self.width = data.get("width")
        self.height = data.get("height")


def _extract_serve_version(result: dict, client: Any) -> str:
    try:
        r = client.get("/api/v1/info")
        r.raise_for_status()
        return r.json().get("version", "docling-serve")
    except Exception:
        return "docling-serve"


def _package_version(package: str) -> str:
    try:
        from importlib.metadata import version as _v
        return _v(package)
    except Exception:
        return "unknown"