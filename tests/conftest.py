"""Shared test configuration."""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = PROJECT_ROOT / "schemas" / "processing_manifest.schema.json"
DATASET_DIR = PROJECT_ROOT / "tests" / "dataset"
DOCUMENTS_DIR = DATASET_DIR / "input"
EXPECTED_DIR = DATASET_DIR / "intermediate" / "processing-manifest"