"""Tests for the processing manifest extraction pipeline."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

from acessilia_extractor.extractors import DoclingExtraction
from acessilia_extractor.manifest.builder import build_processing_manifest
from acessilia_extractor.manifest.schema import processing_manifest_schema, validate_manifest


SCHEMA_PATH = (
    Path(__file__).resolve().parents[1]
    / "schemas"
    / "processing_manifest.schema.json"
)


class FakeDocument:
    def __init__(self) -> None:
        bbox = SimpleNamespace(
            l=10,
            t=20,
            r=200,
            b=80,
            coord_origin=SimpleNamespace(value="TOPLEFT"),
        )
        provenance = SimpleNamespace(page_no=1, bbox=bbox, charspan=(0, 6))
        self.items = [
            (
                SimpleNamespace(
                    label=None,
                    name="body",
                    self_ref="#/body",
                    parent=None,
                ),
                0,
            ),
            (
                SimpleNamespace(
                    label=SimpleNamespace(value="title"),
                    text="Documento de teste",
                    level=1,
                    prov=[provenance],
                    self_ref="#/texts/0",
                    parent=SimpleNamespace(cref="#/body"),
                    content_layer=SimpleNamespace(value="body"),
                ),
                1,
            ),
            (
                SimpleNamespace(
                    label=SimpleNamespace(value="picture"),
                    text="",
                    prov=[provenance],
                    self_ref="#/pictures/0",
                    parent=SimpleNamespace(cref="#/body"),
                ),
                1,
            ),
        ]
        self.pages = {
            1: SimpleNamespace(size=SimpleNamespace(width=595, height=842))
        }

    def iterate_items(self, **_: object):
        return iter(self.items)

    def num_pages(self) -> int:
        return 1


class FakeExtractor:
    def extract(self, _: Path) -> DoclingExtraction:
        timestamp = datetime(2026, 7, 27, tzinfo=timezone.utc)
        return DoclingExtraction(
            document=FakeDocument(),
            started_at=timestamp,
            completed_at=timestamp,
            duration_ms=5,
            version="2.test",
            configuration={"ocr": False},
        )


def test_builds_valid_manifest_and_candidate_obligation(tmp_path: Path):
    source = tmp_path / "sample.pdf"
    source.write_bytes(b"%PDF-test")
    extraction = FakeExtractor().extract(source)
    manifest = build_processing_manifest(source, extraction)
    payload = manifest.model_dump(mode="json", by_alias=True)

    assert payload["$schema"] == "urn:a11y-devs:schema:processing-manifest:1.1.0"
    assert manifest.summary.page_count == 1
    assert manifest.summary.element_count == 3
    assert manifest.elements[1].parent_id == manifest.elements[0].id
    assert manifest.obligations[0].kind == "describe-image"
    assert manifest.obligations[0].selected is False
    assert validate_manifest(payload, SCHEMA_PATH) == []


def test_generated_schema_is_draft_2020_12():
    schema = processing_manifest_schema()

    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert schema["$id"] == "urn:a11y-devs:schema:processing-manifest:1.1.0"
    assert schema["title"] == "ProcessingManifest"
    schema_on_disk = __import__("json").loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    assert schema_on_disk == schema


def test_rejects_unknown_target(tmp_path: Path):
    source = tmp_path / "sample.pdf"
    source.write_bytes(b"%PDF-test")
    extraction = FakeExtractor().extract(source)
    manifest = build_processing_manifest(source, extraction)
    payload = manifest.model_dump(mode="json", by_alias=True)
    payload["obligations"][0]["target_ids"] = ["element-inexistente"]

    errors = validate_manifest(payload)

    assert any("alvos inexistentes" in error for error in errors)


def test_preserves_code_text(tmp_path: Path):
    class CodeDocument:
        def __init__(self) -> None:
            self.pages = {
                1: SimpleNamespace(size=SimpleNamespace(width=600, height=800))
            }
            self.items = [
                (
                    SimpleNamespace(
                        label=None,
                        name="body",
                        self_ref="#/body",
                        parent=None,
                    ),
                    0,
                ),
                (
                    SimpleNamespace(
                        label=SimpleNamespace(value="code"),
                        text="def demo():\n    return 42\n",
                        prov=[
                            SimpleNamespace(
                                page_no=1,
                                bbox=SimpleNamespace(
                                    l=80, t=120, r=520, b=260,
                                    coord_origin=SimpleNamespace(value="TOPLEFT"),
                                ),
                                charspan=(0, 24),
                            )
                        ],
                        self_ref="#/codes/0",
                        parent=SimpleNamespace(cref="#/body"),
                        content_layer=SimpleNamespace(value="body"),
                    ),
                    1,
                ),
            ]

        def iterate_items(self, **_: object):
            return iter(self.items)

        def num_pages(self) -> int:
            return 1

    class CodeExtractor:
        def extract(self, _: Path) -> DoclingExtraction:
            timestamp = datetime(2026, 7, 27, tzinfo=timezone.utc)
            return DoclingExtraction(
                document=CodeDocument(),
                started_at=timestamp,
                completed_at=timestamp,
                duration_ms=5,
                version="2.test",
                configuration={"ocr": False},
            )

    source = tmp_path / "sample.pdf"
    source.write_bytes(b"%PDF-test")
    extraction = CodeExtractor().extract(source)
    manifest = build_processing_manifest(source, extraction)

    code_elements = [e for e in manifest.elements if e.type == "code"]
    assert code_elements
    assert "return 42" in (code_elements[0].text or "")


def test_extracts_table_ast_metadata(tmp_path: Path):
    class TableDocument:
        def __init__(self) -> None:
            self.pages = {
                1: SimpleNamespace(size=SimpleNamespace(width=600, height=800))
            }
            self.items = [
                (
                    SimpleNamespace(
                        label=None,
                        name="body",
                        self_ref="#/body",
                        parent=None,
                    ),
                    0,
                ),
                (
                    SimpleNamespace(
                        label=SimpleNamespace(value="table"),
                        text="",
                        rows=[["Nome", "Valor"], ["Taxa", "10%"]],
                        table={
                            "caption": "Resumo",
                            "header": [
                                {
                                    "cells": [
                                        {"text": "Nome", "scope": "col"},
                                        {"text": "Valor", "scope": "col"},
                                    ]
                                }
                            ],
                            "body": [
                                {
                                    "cells": [
                                        {"text": "Taxa"},
                                        {"text": "10%"},
                                    ]
                                }
                            ],
                        },
                        prov=[
                            SimpleNamespace(
                                page_no=1,
                                bbox=SimpleNamespace(
                                    l=50, t=100, r=550, b=200,
                                    coord_origin=SimpleNamespace(value="TOPLEFT"),
                                ),
                                charspan=None,
                            )
                        ],
                        self_ref="#/tables/0",
                        parent=SimpleNamespace(cref="#/body"),
                        content_layer=SimpleNamespace(value="body"),
                    ),
                    1,
                ),
            ]

        def iterate_items(self, **_: object):
            return iter(self.items)

        def num_pages(self) -> int:
            return 1

    class TableExtractor:
        def extract(self, _: Path) -> DoclingExtraction:
            timestamp = datetime(2026, 7, 27, tzinfo=timezone.utc)
            return DoclingExtraction(
                document=TableDocument(),
                started_at=timestamp,
                completed_at=timestamp,
                duration_ms=5,
                version="2.test",
                configuration={"ocr": False},
            )

    source = tmp_path / "sample.pdf"
    source.write_bytes(b"%PDF-test")
    extraction = TableExtractor().extract(source)
    manifest = build_processing_manifest(source, extraction)

    table_elements = [e for e in manifest.elements if e.type == "table"]
    assert table_elements
    table_metadata = table_elements[0].metadata

    assert "table_ast" in table_metadata
    assert table_metadata["table_ast"]["caption"] == "Resumo"
    assert table_metadata["table_ast"]["header"][0]["cells"][0]["text"] == "Nome"
    assert table_metadata["table_row_count"] == 2
    assert table_metadata["table_column_count"] == 2
    assert table_metadata["table_has_header"] is True