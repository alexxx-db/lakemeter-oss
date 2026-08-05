"""Contracts for release-hygiene wave: grants, root docs, pricing job naming."""
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[1]
SCRIPTS = REPO / "scripts"
BUNDLE = SCRIPTS / "databricks.yml"


def test_legacy_installer_has_no_all_privileges_table_grants():
    text = (SCRIPTS / "install_lakemeter.py").read_text()
    assert "apply_app_role_grants" in text
    assert "GRANT ALL PRIVILEGES ON ALL TABLES" not in text


def test_architecture_docs_match_current_auth_and_job():
    arch = (REPO / "ARCHITECTURE.md").read_text()
    assert "JWT_SECRET_KEY" not in arch
    assert "no" in arch.lower() and "application-issued JWT" in arch
    assert "lakemeter_pricing_refresh" in arch
    assert "lakemeter_pricing_sync" not in arch
    assert "admin user list" not in arch


def test_root_changelog_mentions_hardening_and_refresh_job():
    cl = (REPO / "CHANGELOG.md").read_text()
    assert "lakemeter_pricing_refresh" in cl
    assert "Least-privilege" in cl or "least-privilege" in cl
    assert "enable_pg_native_login" in cl
    # Stale job name from older Unreleased notes must be gone
    assert "lakemeter_pricing_sync" not in cl


def test_bundle_pricing_job_name_is_refresh():
    data = yaml.safe_load(BUNDLE.read_text())
    jobs = data["resources"]["jobs"]
    assert "lakemeter_pricing_refresh" in jobs
    assert "lakemeter_pricing_sync" not in jobs


def test_autoscaling_enables_native_login_on_create():
    text = (SCRIPTS / "lakebase_autoscaling.py").read_text()
    assert "enable_pg_native_login=True" in text
    assert "_ensure_pg_native_login" in text
