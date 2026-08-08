"""Structural contract tests for the W5 reporting package: UC reporting
tables, AI/BI dashboard template, Genie space template, bundle wiring."""

import json
import re
from pathlib import Path

import pytest
import yaml

REPO = Path(__file__).resolve().parent.parent
NOTEBOOK = REPO / "scripts" / "notebooks" / "14_package_reporting.py"
DASHBOARD = REPO / "scripts" / "notebooks" / "reporting" / "lakemeter_costs.lvdash.json"
GENIE = REPO / "scripts" / "notebooks" / "reporting" / "lakemeter_genie_space.json"
BUNDLE = REPO / "scripts" / "databricks.yml"
INSTALLER = REPO / "docs-site" / "docs" / "admin-guide" / "installer.md"
INVENTORY = REPO / "docs-site" / "docs" / "admin-guide" / "deployment-inventory.md"

nb = NOTEBOOK.read_text()
bundle = yaml.safe_load(BUNDLE.read_text())
dashboard = json.loads(DASHBOARD.read_text())
genie = json.loads(GENIE.read_text())

pytestmark = pytest.mark.structural

RPT_TABLES = ["rpt_spend_daily", "rpt_spend_daily_by_product",
              "rpt_genie_queries_daily", "rpt_dashboard_queries_daily",
              "rpt_budget_alerts"]


def test_notebook_exists():
    assert NOTEBOOK.exists()


def test_dashboard_template_valid_and_placeholdered():
    assert "${catalog}" in DASHBOARD.read_text()
    assert "${schema}" in DASHBOARD.read_text()
    names = {d["name"] for d in dashboard["datasets"]}
    assert names == {"spend_daily", "spend_by_product", "genie_activity",
                     "dashboard_activity", "budget_alerts"}
    pages = {p["name"] for p in dashboard["pages"]}
    assert pages == {"overview", "genie_dashboards"}
    for page in dashboard["pages"]:
        assert page["layout"], page["name"]


def test_genie_template_valid():
    tables = {t["identifier"] for t in genie["data_sources"]["tables"]}
    expected = {f"${{catalog}}.${{schema}}.{t}" for t in RPT_TABLES}
    assert tables == expected
    content = genie["instructions"]["text_instructions"][0]["content"]
    joined = " ".join(content)
    for term in ["list_cost", "confidence", "cost_center", "2027-01-31"]:
        assert term in joined, term
    assert genie["instructions"]["example_questions"]
    assert genie["config"]["sample_questions"]


def test_notebook_writes_all_rpt_tables():
    for table in RPT_TABLES:
        assert f'"{table}"' in nb, table
    assert nb.count("saveAsTable") >= 1
    assert "CREATE SCHEMA IF NOT EXISTS" in nb
    # sources stay in Lakebase; targets in UC
    assert "FROM lakemeter.attribution_daily a" in nb
    assert "FROM lakemeter.product_usage_daily" in nb
    assert "FROM lakemeter.genie_query_daily" in nb
    assert "FROM lakemeter.dashboard_query_daily" in nb
    assert "FROM lakemeter.budget_alerts" in nb


def test_notebook_deploys_dashboard_and_genie():
    assert "lakemeter_costs.lvdash.json" in nb
    assert "lakemeter_genie_space.json" in nb
    assert "dbutils.fs.put" in nb
    assert "w.genie.create_space" in nb or "genie.create_space" in nb
    # genie API failures must not fail the job
    assert "except Exception" in nb
    # placeholders fully rendered before deploy
    assert nb.count('replace("${catalog}", catalog)') == 2
    assert nb.count('replace("${schema}", schema)') == 2


def test_empty_rollup_handled():
    assert "if rows:" in nb and "else:" in nb
    assert "STRING" in nb  # empty-frame schema fallback


def test_bundle_reporting_job():
    job = bundle["resources"]["jobs"]["lakemeter_reporting_package"]
    assert job["schedule"]["pause_status"] == "${var.reporting_package_pause_status}"
    assert bundle["variables"]["reporting_package_pause_status"]["default"] == "PAUSED"
    task = job["tasks"][0]
    assert task["notebook_task"]["notebook_path"] == "./notebooks/14_package_reporting.py"
    params = task["notebook_task"]["base_parameters"]
    assert params["reporting_catalog"] == "{{job.parameters.reporting_catalog}}"
    assert params["reporting_schema"] == "{{job.parameters.reporting_schema}}"


def test_genie_free_window_documented():
    assert "2027-01-31" in nb


def test_docs_cover_reporting_package():
    installer = INSTALLER.read_text()
    for term in ["Reporting Package", "rpt_spend_daily", "lakemeter_costs.lvdash.json",
                 "Lakemeter Cost Attribution", "reporting_package_pause_status"]:
        assert term in installer, term
    inventory = INVENTORY.read_text()
    for term in ["rpt_spend_daily", "Lakemeter Cost Attribution",
                 "lakemeter_costs.lvdash.json", "Lakemeter Reporting Package"]:
        assert term in inventory, term
