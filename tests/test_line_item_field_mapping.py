"""Contracts for line-item API ↔ storage column mapping."""
import os
import sys

os.environ.setdefault("DATABASE_URL", "postgresql://u:p@localhost:5432/db")
os.environ.setdefault("ENVIRONMENT", "local")

BACKEND_DIR = os.path.join(os.path.dirname(__file__), "..", "backend")
sys.path.insert(0, BACKEND_DIR)

from app.schemas.line_item import (
    map_ai_parse_api_fields,
    map_line_item_api_fields,
    map_shutterstock_fields,
)


def test_shutterstock_images_syncs_legacy_column():
    data = map_shutterstock_fields(
        {"shutterstock_images": 500},
        {"shutterstock_images"},
    )
    assert data["shutterstock_images"] == 500
    assert data["shutterstock_imageai_num_images"] == 500


def test_shutterstock_legacy_syncs_ui_column():
    data = map_shutterstock_fields(
        {"shutterstock_imageai_num_images": 42},
        {"shutterstock_imageai_num_images"},
    )
    assert data["shutterstock_images"] == 42


def test_ai_parse_keeps_ui_columns_and_sets_storage():
    data = map_ai_parse_api_fields(
        {"ai_parse_mode": "pages", "ai_parse_pages_thousands": 10},
        {"ai_parse_mode", "ai_parse_pages_thousands"},
    )
    assert data["ai_parse_mode"] == "pages"
    assert data["ai_parse_pages_thousands"] == 10
    assert data["ai_parse_calculation_method"] == "pages_based"
    assert data["ai_parse_num_pages"] == 10000


def test_combined_mapper_covers_connect_and_shutterstock():
    data = map_line_item_api_fields(
        {
            "shutterstock_images": 100,
            "lakeflow_connect_gateway_instance": "i3.xlarge",
        },
        {"shutterstock_images", "lakeflow_connect_gateway_instance"},
    )
    assert data["shutterstock_imageai_num_images"] == 100
    assert data["lakeflow_connect_gateway_instance_type"] == "i3.xlarge"
