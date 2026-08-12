"""Structural contract tests for the attribution build (W2).

These tests validate the notebook, bundle wiring, and docs coverage
statically, so they run anywhere without a Databricks workspace or a
Lakebase instance.
"""

import re
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parent.parent
NOTEBOOK = REPO / "scripts" / "notebooks" / "09_build_attribution.py"
BUNDLE = REPO / "scripts" / "databricks.yml"
INSTALLER = REPO / "docs-site" / "docs" / "admin-guide" / "installer.md"
INVENTORY = REPO / "docs-site" / "docs" / "admin-guide" / "deployment-inventory.md"

nb = NOTEBOOK.read_text()
bundle = yaml.safe_load(BUNDLE.read_text())


def test_notebook_exists():
    assert NOTEBOOK.exists()


def test_creates_attribution_daily():
    assert "CREATE TABLE IF NOT EXISTS lakemeter.attribution_daily" in nb
    for col in [
        "usage_date", "attributed_user", "attribution_source",
        "attribution_confidence", "cost_center", "sku_name", "cloud",
        "asset_type", "asset_id", "usage_quantity", "list_cost",
        "currency_code", "record_count",
    ]:
        assert re.search(rf"\b{col}\b", nb), col


def test_creates_cost_center_map():
    assert "CREATE TABLE IF NOT EXISTS lakemeter.ref_user_cost_center_map" in nb
    assert "user_email TEXT PRIMARY KEY" in nb
    assert "cost_center TEXT NOT NULL" in nb


def test_attribution_chain_order():
    """run_as wins over owned_by, then created_by, then the owner tag,
    then UNATTRIBUTED."""
    m = re.search(r"COALESCE\((.*?)\) AS attributed_user", nb, re.S)
    assert m, "attributed_user COALESCE not found"
    body = m.group(1)
    order = [
        body.index("a.run_as"),
        body.index("a.owned_by"),
        body.index("a.created_by"),
        body.index("custom_tags ->> 'owner'"),
        body.index("'UNATTRIBUTED'"),
    ]
    assert order == sorted(order)


def test_confidence_grades():
    assert "'HIGH'" in nb and "'MEDIUM'" in nb and "'LOW'" in nb and "'NONE'" in nb
    # HIGH only for run_as
    high = re.search(r"WHEN NULLIF\(a.run_as, ''\) IS NOT NULL THEN 'HIGH'", nb)
    assert high


def test_cost_center_fallback_chain():
    m = re.search(r"COALESCE\(m.cost_center, t.tag_cost_center, 'UNMAPPED'\)", nb)
    assert m
    assert re.search(
        r"LEFT JOIN lakemeter.ref_user_cost_center_map m\s+ON m.user_email = t.attributed_user",
        nb,
    )


def test_asset_type_derivation():
    for asset in ["sql_warehouse", "model_serving", "dlt_pipeline", "job", "cluster", "other"]:
        assert f"'{asset}'" in nb


def test_reads_actuals_usage_daily():
    assert "FROM lakemeter.actuals_usage_daily" in nb


def test_incremental_window_delete_insert():
    assert re.search(r"DELETE FROM lakemeter.attribution_daily\s+WHERE usage_date >=", nb)
    assert "INSERT INTO lakemeter.attribution_daily" in nb
    assert "reprocess_days" in nb
    assert "initial_backfill_days" in nb


def test_window_start_is_single_literal():
    assert 'window_start_sql = f"DATE \'{window_start}\'"' in nb
    assert nb.count("window_start_sql") >= 3  # defined, DELETE, INSERT
    assert "current_date" not in nb  # Spark-only expression must not leak into Postgres


def test_watermark_uses_shared_state_table():
    assert "lakemeter.actuals_ingestion_state" in nb
    assert "'attribution_daily'" in nb
    assert "ON CONFLICT (pipeline_name) DO NOTHING" in nb


def test_unattributed_warning():
    assert "UNATTRIBUTED" in nb
    assert "0.20" in nb or "20%" in nb
    assert "WARNING" in nb


def test_bundle_has_build_attribution_task():
    job = bundle["resources"]["jobs"]["lakemeter_actuals_sync"]
    tasks = {t["task_key"]: t for t in job["tasks"]}
    assert "build_attribution" in tasks
    task = tasks["build_attribution"]
    assert task["notebook_task"]["notebook_path"] == "./notebooks/09_build_attribution.py"
    assert task["depends_on"] == [{"task_key": "sync_actuals_usage"}]
    assert task["environment_key"] == "serverless_env"
    params = task["notebook_task"]["base_parameters"]
    assert params == {
        "instance_name": "{{job.parameters.instance_name}}",
        "db_name": "{{job.parameters.db_name}}",
        "secrets_scope": "{{job.parameters.secrets_scope}}",
    }


def test_docs_cover_attribution():
    installer = INSTALLER.read_text()
    assert "Attribution Build" in installer
    assert "attribution_daily" in installer
    assert "ref_user_cost_center_map" in installer
    inventory = INVENTORY.read_text()
    assert "attribution_daily" in inventory
    assert "ref_user_cost_center_map" in inventory
