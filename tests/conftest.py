"""Shared test configuration."""

from pathlib import Path

# Ensure the schema path is discoverable
SCHEMA_PATH = Path(__file__).resolve().parents[1] / "schemas" / "processing_manifest.schema.json"