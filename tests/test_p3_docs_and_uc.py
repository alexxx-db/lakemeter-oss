"""Contracts for P3 docs, sidebars, and UC pricing refresh scaffolding."""
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[1]
DOCS = REPO / "docs-site" / "docs"
SIDEBARS = REPO / "docs-site" / "sidebars.ts"
BUNDLE = REPO / "scripts" / "databricks.yml"
NOTEBOOKS = REPO / "scripts" / "notebooks"


def test_lakeflow_connect_guide_and_catalog():
    connect = (DOCS / "user-guide" / "lakeflow-connect.md").read_text()
    assert "Lakeflow Connect" in connect
    assert "DLT Serverless" in connect
    assert "Gateway" in connect

    workloads = (DOCS / "user-guide" / "workloads.md").read_text()
    assert "lakeflow-connect" in workloads
    assert "Commercial items" in workloads or "commercial" in workloads.lower()
    assert "databricks_support" in workloads or "Support" in workloads


def test_sidebars_include_connect_pricing_architecture():
    text = SIDEBARS.read_text()
    assert "user-guide/lakeflow-connect" in text
    assert "admin-guide/pricing-data" in text
    assert "admin-guide/architecture" in text


def test_admin_pricing_and_architecture_docs():
    pricing = (DOCS / "admin-guide" / "pricing-data.md").read_text()
    assert "unity_catalog" in pricing
    assert "bundled_csv" in pricing
    assert "10_refresh_pricing_from_uc" in pricing

    arch = (DOCS / "admin-guide" / "architecture.md").read_text()
    assert "AppKit" in arch
    assert "Lakebase" in arch
    assert "when not" in arch.lower() or "Keep the current" in arch


def test_uc_refresh_notebook_and_job_params():
    nb = (NOTEBOOKS / "10_refresh_pricing_from_uc.py").read_text()
    assert "unity_catalog" in nb
    assert "dbu_prices" in nb
    assert "sync_pricing_dbu_rates" in nb

    refresh = (NOTEBOOKS / "09_refresh_pricing.py").read_text()
    assert "pricing_source" in refresh
    assert "10_refresh_pricing_from_uc" in refresh

    data = yaml.safe_load(BUNDLE.read_text())
    job = data["resources"]["jobs"]["lakemeter_pricing_refresh"]
    param_names = {p["name"] for p in job["parameters"]}
    assert "pricing_source" in param_names
    assert "uc_catalog" in param_names
    task = next(t for t in job["tasks"] if t["task_key"] == "refresh_pricing")
    assert "pricing_source" in task["notebook_task"]["base_parameters"]


def test_workload_types_include_lakeflow_connect():
    wt = (REPO / "backend" / "app" / "routes" / "workload_types.py").read_text()
    assert '"workload_type": "LAKEFLOW_CONNECT"' in wt
    assert "DELTA_LIVE_TABLES_SERVERLESS" in wt
