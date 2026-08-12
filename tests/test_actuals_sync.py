"""Structural tests for the actuals (usage) ingestion pipeline (W1).

The sync notebook (scripts/notebooks/08_sync_actuals.py) runs inside a
Databricks workspace, so it cannot be imported by pytest. These tests pin
its contract instead: table DDL, watermark-based incremental behavior,
idempotent DELETE + INSERT reprocess window, correction-record handling,
bundle job wiring, and documentation.
"""
import re
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
NOTEBOOK = REPO_ROOT / "scripts" / "notebooks" / "08_sync_actuals.py"
BUNDLE = REPO_ROOT / "scripts" / "databricks.yml"
INSTALLER_DOC = REPO_ROOT / "docs-site" / "docs" / "admin-guide" / "installer.md"
INVENTORY_DOC = REPO_ROOT / "docs-site" / "docs" / "admin-guide" / "deployment-inventory.md"

IDENTITY_COLUMNS = ["run_as", "owned_by", "created_by"]
ASSET_COLUMNS = [
    "warehouse_id", "endpoint_id", "endpoint_name",
    "cluster_id", "job_id", "dlt_pipeline_id", "node_type",
]


def notebook_text() -> str:
    return NOTEBOOK.read_text(encoding="utf-8")


def bundle_dict() -> dict:
    return yaml.safe_load(BUNDLE.read_text(encoding="utf-8"))


def test_notebook_exists():
    assert NOTEBOOK.exists(), "08_sync_actuals.py notebook missing"


def test_creates_actuals_table_with_core_columns():
    t = notebook_text()
    assert "CREATE TABLE IF NOT EXISTS lakemeter.actuals_usage_daily" in t
    for col in ["usage_date", "record_id", "record_type", "workspace_id",
                "sku_name", "cloud", "usage_unit", "usage_quantity",
                "list_price", "list_cost", "custom_tags"]:
        assert col in t, f"missing column {col}"


def test_identity_columns_present_for_attribution():
    t = notebook_text()
    for col in IDENTITY_COLUMNS:
        assert col in t, f"missing identity column {col}"
    assert "u.identity_metadata.run_as" in t
    assert "u.identity_metadata.owned_by" in t
    assert "u.identity_metadata.created_by" in t


def test_asset_columns_cover_warehouses_endpoints_clusters_jobs_pipelines():
    t = notebook_text()
    for col in ASSET_COLUMNS:
        assert col in t, f"missing asset column {col}"


def test_reads_system_billing_tables():
    t = notebook_text()
    assert "FROM system.billing.usage u" in t
    assert "LEFT JOIN system.billing.list_prices p" in t
    assert "p.effective_list.default" in t


def test_unpriced_rows_kept_and_counted():
    t = notebook_text()
    assert "LEFT JOIN" in t, "pricing join must be LEFT so unpriced rows are kept"
    assert "list_price IS NULL" in t, "unpriced rows must be counted"
    assert "WARNING" in t


def test_watermark_table_and_state():
    t = notebook_text()
    assert "CREATE TABLE IF NOT EXISTS lakemeter.actuals_ingestion_state" in t
    assert "watermark_date" in t
    assert "pipeline_name" in t


def test_idempotent_delete_insert_window():
    t = notebook_text()
    assert re.search(r"DELETE FROM lakemeter\.actuals_usage_daily\s+WHERE usage_date >=", t)
    assert "INSERT INTO lakemeter.actuals_usage_daily" in t
    assert "reprocess_days" in t
    assert "initial_backfill_days" in t


def test_correction_records_documented_and_preserved():
    t = notebook_text()
    # No filtering on record_type: corrections (negative quantities) must load
    assert "record_type" in t
    assert "CORRECTION" in t.upper()
    where_block = re.search(r"WHERE u\.usage_date >=.*?\n", t)
    assert where_block and "record_type" not in where_block.group(0), \
        "WHERE clause must not filter out correction records"


def test_window_start_is_single_literal_used_in_both_engines():
    t = notebook_text()
    assert "window_start_sql = f\"DATE '{window_start}'\"" in t
    # Spark query and Postgres DELETE both reference the same literal
    assert "WHERE u.usage_date >= {window_start_sql}" in t
    assert "WHERE usage_date >= {window_start_sql}" in t


def test_bundle_has_actuals_job_paused_by_default():
    y = bundle_dict()
    var = y["variables"]["actuals_sync_pause_status"]
    assert var["default"] == "PAUSED"
    job = y["resources"]["jobs"]["lakemeter_actuals_sync"]
    assert job["schedule"]["pause_status"] == "${var.actuals_sync_pause_status}"
    assert job["schedule"]["timezone_id"] == "UTC"


def test_bundle_job_is_daily_and_serverless():
    job = bundle_dict()["resources"]["jobs"]["lakemeter_actuals_sync"]
    cron = job["schedule"]["quartz_cron_expression"]
    assert cron.split()[3] == "*", f"expected daily cron, got {cron}"
    task = job["tasks"][0]
    assert task["notebook_task"]["notebook_path"] == "./notebooks/08_sync_actuals.py"
    assert task["environment_key"] == "serverless_env"


def test_job_parameters_match_installer_conventions():
    params = {p["name"]: p["default"]
              for p in bundle_dict()["resources"]["jobs"]["lakemeter_actuals_sync"]["parameters"]}
    assert params == {
        "instance_name": "lakemeter-customer",
        "db_name": "lakemeter_pricing",
        "secrets_scope": "lakemeter-secrets",
    }


def test_installer_doc_covers_actuals_sync():
    t = INSTALLER_DOC.read_text(encoding="utf-8")
    assert "Actuals Usage Sync" in t
    assert "actuals_sync_pause_status=UNPAUSED" in t
    assert "actuals_usage_daily" in t


def test_inventory_doc_lists_job_and_tables():
    t = INVENTORY_DOC.read_text(encoding="utf-8")
    assert "Lakemeter Actuals Sync" in t
    assert "actuals_ingestion_state" in t
