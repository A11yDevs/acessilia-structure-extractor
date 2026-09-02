"""Extraction backends — base interface and implementations.

Cada backend de extração é um microserviço acessado via REST.
O Acessilia Extractor atua como agregador, roteando requisições
para o backend apropriado e normalizando o resultado no
Processing Manifest canônico.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter
from typing import Any


@dataclass(frozen=True)
class ExtractionResult:
    """Resultado normalizado de uma extração de documento.

    Attributes:
        document: Objeto documento extraído (formato específico do backend).
        backend: Nome do backend que produziu a extração.
        started_at: Momento do início da extração.
        completed_at: Momento da conclusão.
        duration_ms: Duração total em milissegundos.
        version: Versão do backend/extrator.
        configuration: Configuração usada na extração.
    """
    document: Any
    backend: str
    started_at: datetime
    completed_at: datetime
    duration_ms: int
    version: str
    configuration: dict[str, Any]


class BaseExtractor(ABC):
    """Interface comum para extratores de documentos."""

    @abstractmethod
    def extract(self, source_path: Path) -> ExtractionResult:
        """Extrai a estrutura de um documento."""
        ...


class DoclingServeExtractor(BaseExtractor):
    """Extrator remoto via docling-serve (API REST v1).

    O docling-serve deve estar rodando em um host acessível.
    Docker recomendado:

        docker run -p 5001:5001 -v docling-models:/root/.cache/docling \\
            ghcr.io/docling-project/docling-serve-cpu:latest
    """

    def __init__(self, base_url: str = "http://docling-serve:5001"):
        self.base_url = base_url.rstrip("/")

    def extract(self, source_path: Path) -> ExtractionResult:
        import httpx

        source_path = source_path.resolve()
        if not source_path.is_file():
            raise FileNotFoundError(f"Documento não encontrado: {source_path}")

        started_at = datetime.now(timezone.utc)
        started_clock = perf_counter()

        with httpx.Client(base_url=self.base_url, timeout=600) as client:
            with source_path.open("rb") as f:
                upload_resp = client.post(
                    "/v1/convert/file",
                    files={"files": (source_path.name, f, "application/pdf")},
                    data={"to_formats": ["json"]},
                )
            upload_resp.raise_for_status()
            result = upload_resp.json()

            doc_entry = result.get("document") or {}
            json_content = doc_entry.get("json_content")
            if json_content is not None:
                docling_doc = json_content
            else:
                docling_doc = result

        duration_ms = round((perf_counter() - started_clock) * 1000)
        completed_at = datetime.now(timezone.utc)

        return ExtractionResult(
            document=_BuildDoclingDocument(docling_doc),
            backend="docling",
            started_at=started_at,
            completed_at=completed_at,
            duration_ms=duration_ms,
            version=_extract_serve_version(client),
            configuration={
                "extractor": "docling-serve",
                "base_url": self.base_url,
            },
        )


class _BuildDoclingDocument:
    """Wrapper para compatibilizar o DoclingDocument v2 (docling-serve 1.30+)
    com a interface esperada pelo builder (iterate_items, pages, num_pages).

    O novo formato tem coleções separadas: texts, pictures, tables, groups, etc.
    O body é uma árvore com children que referenciam itens via $ref.
    """

    def __init__(self, payload: dict[str, Any]) -> None:
        self._payload = payload
        self._items: list[tuple[Any, int]] = []
        self._build_items()

    def _build_items(self) -> None:
        # Coleções de itens no novo formato
        collections = {
            "texts": 1,
            "pictures": 1,
            "tables": 1,
            "groups": 1,
            "key_value_items": 1,
            "form_items": 1,
        }
        seen: set[str] = set()
        for coll_name, default_level in collections.items():
            items = self._payload.get(coll_name, [])
            for item in items:
                ref = item.get("self_ref", "")
                if ref and ref in seen:
                    continue
                if ref:
                    seen.add(ref)
                level = item.get("level", default_level)
                if isinstance(level, dict):
                    level = 1
                self._items.append((_ItemProxy(item), level))

    def iterate_items(self, **kwargs: Any) -> Any:
        return iter(self._items)

    def num_pages(self) -> int:
        pages = self._payload.get("pages", {})
        if isinstance(pages, dict):
            return len(pages)
        if isinstance(pages, list):
            return len(pages)
        return 0

    @property
    def pages(self) -> dict[int, Any]:
        pages = self._payload.get("pages", {})
        if isinstance(pages, dict):
            return {
                int(k): _PageProxy(v) for k, v in pages.items()
            }
        if isinstance(pages, list):
            return {
                p.get("page_number", i): _PageProxy(p)
                for i, p in enumerate(pages)
            }
        return {}


class _ItemProxy:
    """Proxy para itens individuais do documento Docling v2."""

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
            val = self._data.get(name)
            if isinstance(val, dict):
                return None
            return val
        if name in ("text", "orig", "name", "marker", "enumerated", "content_layer"):
            return self._data.get(name)
        if name == "table":
            return self._data.get("table") or self._data.get("data")
        for candidate in ("rows", "data", "cells"):
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


def _extract_serve_version(client: Any) -> str:
    try:
        r = client.get("/version")
        r.raise_for_status()
        data = r.json()
        return data.get("version") or data.get("docling_serve_version", "docling-serve")
    except Exception:
        return "docling-serve"


def _package_version(package: str) -> str:
    try:
        from importlib.metadata import version as _v
        return _v(package)
    except Exception:
        return "unknown"