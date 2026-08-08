"""Contracts for Live FinOps P0 scaffold (ADR-012)."""

from __future__ import annotations

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
FINOPS = ROOT / "etl" / "finops"
NOTEBOOK = FINOPS / "notebooks" / "01_build_finops_gold.py"
SQL = FINOPS / "sql" / "cost_daily.sql"
BUNDLE = FINOPS / "databricks.yml"
DECISIONS = ROOT / "DECISIONS.md"


def test_adr_012_exists():
    text = DECISIONS.read_text()
    assert "## ADR-012: Live FinOps" in text
    assert "system.billing.usage" in text
    assert "list_prices" in text
    assert "Lakebase" in text


def test_finops_bundle_job_paused():
    cfg = yaml.safe_load(BUNDLE.read_text())
    job = cfg["resources"]["jobs"]["lakemeter_finops_gold"]
    assert job["schedule"]["pause_status"] == "PAUSED"
    assert job["max_concurrent_runs"] == 1
    task = job["tasks"][0]
    assert task["task_key"] == "build_finops_gold"
    assert "01_build_finops_gold" in task["notebook_task"]["notebook_path"]


def test_join_semantics_in_notebook_and_sql():
    notebook = NOTEBOOK.read_text()
    sql = SQL.read_text()
    for blob in (notebook, sql):
        assert "system.billing.usage" in blob
        assert "system.billing.list_prices" in blob
        assert "lp.sku_name = u.sku_name" in blob
        assert "usage_end_time >= lp.price_start_time" in blob
        assert "price_end_time IS NULL OR u.usage_end_time < lp.price_end_time" in blob
        assert "billing_origin_product" in blob
        assert "list_cost_usd" in blob
        assert "custom_tags['lakemeter_estimate_id']" in blob


def test_gold_tables_named():
    notebook = NOTEBOOK.read_text()
    for table in (
        "cost_daily",
        "cost_by_product_daily",
        "cost_by_estimate_daily",
        "finops_run_metadata",
    ):
        assert table in notebook
    assert "cost_basis" in notebook
    assert "list" in notebook
    assert "lakemeter_estimate_id" in notebook
    assert "custom_tags" in notebook


def test_tagging_contract_doc():
    tagging = (FINOPS / "TAGGING.md").read_text()
    assert "lakemeter_estimate_id" in tagging
    assert "lakemeter_workload_type" in tagging


def test_frontend_tag_keys_match_contract():
    tags_ts = (ROOT / "frontend" / "src" / "lib" / "finopsTags.ts").read_text()
    assert "lakemeter_estimate_id" in tags_ts
    assert "lakemeter_workload_type" in tags_ts
    assert "lakemeter_line_item_id" in tags_ts
    finops_py = (ROOT / "backend" / "app" / "services" / "finops.py").read_text()
    assert 'TAG_ESTIMATE_ID = "lakemeter_estimate_id"' in finops_py


def test_admin_finops_doc_exists():
    doc = ROOT / "docs-site" / "docs" / "admin-guide" / "finops.md"
    assert doc.is_file()
    text = doc.read_text()
    assert "FINOPS_WAREHOUSE_ID" in text
    assert "lakemeter_estimate_id" in text


def test_readme_points_to_adr():
    readme = (FINOPS / "README.md").read_text()
    assert "ADR-012" in readme
    assert "PAUSED" in readme.upper() or "paused" in readme
