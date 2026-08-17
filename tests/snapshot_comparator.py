"""Comparador de snapshots — normaliza e compara ProcessingManifests.

Remove campos voláteis (timestamps, caminhos, hashes, IDs) para comparar
apenas a estrutura semântica do documento extraído.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


# Campos que SEMPRE divergem entre execuções
VOLATILE_ROOT_FIELDS = {
    "manifest_id",
    "revision",
    "status",
    "created_at",
    "$schema",
    "schema_version",
}

VOLATILE_ELEMENT_FIELDS = {
    "id",
    "source_ref",
    "parent_ref",
    "parent_id",
    "confidence",
}

VOLATILE_EXTRACTOR_FIELDS = {
    "version",
    "started_at",
    "completed_at",
    "duration_ms",
}

VOLATILE_SOURCE_FIELDS = {
    "document_id",
    "path",
    "sha256",
    "byte_size",
}


def _strip_keys(obj: dict, keys: set[str]) -> None:
    for key in list(obj.keys()):
        if key in keys:
            del obj[key]


def _normalize_manifest(manifest: dict) -> dict:
    """Retorna cópia com campos voláteis removidos."""
    m = json.loads(json.dumps(manifest))

    _strip_keys(m, VOLATILE_ROOT_FIELDS)

    if "source" in m:
        _strip_keys(m["source"], VOLATILE_SOURCE_FIELDS)

    if "extractor" in m:
        _strip_keys(m["extractor"], VOLATILE_EXTRACTOR_FIELDS)

    for element in m.get("elements", []):
        _strip_keys(element, VOLATILE_ELEMENT_FIELDS)
        # Remove proveniência (coordenadas absolutas)
        element.pop("provenance", None)
        # Normaliza metadata: só tabela importa
        if "metadata" in element:
            element["metadata"] = _normalize_metadata(element["metadata"])

    for page in m.get("pages", []):
        page.pop("element_ids", None)

    for obs in m.get("observations", []):
        obs.pop("id", None)

    for obl in m.get("obligations", []):
        obl.pop("id", None)
        obl.pop("target_ids", None)

    return m


def _normalize_metadata(metadata: dict) -> dict:
    """Mantém só metadados estruturais, descarta versão-dependentes."""
    keep = {}
    for key in (
        "table_ast", "table_row_count", "table_column_count",
        "table_has_header", "table_linearization_hint",
        "enumerated", "marker", "content_layer",
        "docling_class",
    ):
        if key in metadata:
            keep[key] = metadata[key]
    return keep


def compare_manifests(
    expected_path: Path,
    actual_path: Path,
) -> list[str]:
    """Compara dois manifests e retorna lista de diferenças."""
    expected = json.loads(expected_path.read_text(encoding="utf-8"))
    actual = json.loads(actual_path.read_text(encoding="utf-8"))

    exp_norm = _normalize_manifest(expected)
    act_norm = _normalize_manifest(actual)

    diffs: list[str] = []

    # 1. Comparação de alto nível
    scalar_checks = [
        ("title", "title"),
        ("language", "language"),
        ("num_pages", lambda m: len(m.get("pages", []))),
        ("num_elements", lambda m: len(m.get("elements", []))),
        ("num_observations", lambda m: len(m.get("observations", []))),
        ("num_obligations", lambda m: len(m.get("obligations", []))),
    ]

    for name, accessor in scalar_checks:
        ev = accessor(exp_norm) if callable(accessor) else exp_norm.get(accessor)
        av = accessor(act_norm) if callable(accessor) else act_norm.get(accessor)
        if ev != av:
            diffs.append(f"{name}: esperado={ev}, obtido={av}")

    # 2. Summary
    if exp_norm.get("summary") != act_norm.get("summary"):
        diffs.append(f"summary: esperado={exp_norm.get('summary')}, obtido={act_norm.get('summary')}")

    # 3. Elementos (tipo, label, hierarquia)
    for i, (ee, ae) in enumerate(zip(exp_norm.get("elements", []), act_norm.get("elements", []))):
        for key in ("type", "raw_label", "hierarchy_level", "reading_order", "page_number"):
            ev = ee.get(key)
            av = ae.get(key)
            if ev != av:
                diffs.append(f"elements[{i}].{key}: esperado={ev}, obtido={av}")

    # Verificar se o número de elementos é o mesmo
    if len(exp_norm.get("elements", [])) != len(act_norm.get("elements", [])):
        diffs.append(
            f"element_count: esperado={len(exp_norm.get('elements', []))}, "
            f"obtido={len(act_norm.get('elements', []))}"
        )

    # 4. Obrigações
    for i, (eo, ao) in enumerate(zip(
        exp_norm.get("obligations", []),
        act_norm.get("obligations", []),
    )):
        if eo.get("kind") != ao.get("kind"):
            diffs.append(f"obligations[{i}].kind: esperado={eo.get('kind')}, obtido={ao.get('kind')}")
        if eo.get("rationale") != ao.get("rationale"):
            diffs.append(f"obligations[{i}].rationale: esperado={eo.get('rationale')}, obtido={ao.get('rationale')}")

    if len(exp_norm.get("obligations", [])) != len(act_norm.get("obligations", [])):
        diffs.append(
            f"obligation_count: esperado={len(exp_norm.get('obligations', []))}, "
            f"obtido={len(act_norm.get('obligations', []))}"
        )

    return diffs