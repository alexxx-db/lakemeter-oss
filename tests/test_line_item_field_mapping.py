"""Contracts for line-item API ↔ storage column mapping."""
import os
import sys

os.environ.setdefault("DATABASE_URL", "postgresql://u:p@localhost:5432/db")
os.environ.setdefault("ENVIRONMENT", "local")

BACKEND_DIR = os.path.join(os.path.dirname(__file__), "..", "backend")
sys.path.insert(0, BACKEND_DIR)

from app.schemas.line_item import map_ai_parse_api_fields


def test_shutterstock_images_syncs_legacy_column():
    data = map_ai_parse_api_fields(
        {"shutterstock_images": 500},
        {"shutterstock_images"},
    )
    assert data["shutterstock_imageai_num_images"] == 500
    assert "shutterstock_images" not in data


def test_ai_parse_keeps_ui_columns_and_sets_storage():
    data = map_ai_parse_api_fields(
        {"ai_parse_mode": "pages", "ai_parse_pages_thousands": 10},
        {"ai_parse_mode", "ai_parse_pages_thousands"},
    )
    assert data["ai_parse_calculation_method"] == "pages_based"
    assert data["ai_parse_num_pages"] == 10000
    assert "ai_parse_mode" not in data
    assert "ai_parse_pages_thousands" not in data
