"""Static contracts for the installer Databricks Asset Bundle."""
from pathlib import Path

import yaml

BUNDLE = Path(__file__).resolve().parents[1] / "scripts" / "databricks.yml"


def _load():
    return yaml.safe_load(BUNDLE.read_text())


def test_bundle_has_dev_staging_prod_targets():
    data = _load()
    targets = data.get("targets") or {}
    assert "dev" in targets
    assert "staging" in targets
    assert "prod" in targets
    assert targets["dev"].get("default") is True


def test_installer_job_has_timeouts_and_concurrency():
    data = _load()
    job = data["resources"]["jobs"]["lakemeter_installer"]
    assert job.get("max_concurrent_runs") == 1
    assert job.get("timeout_seconds", 0) >= 3600
    tasks = {t["task_key"]: t for t in job["tasks"]}
    assert tasks["deploy_app"]["timeout_seconds"] >= 1800
    assert tasks["verify_installation"]["timeout_seconds"] >= 600


def test_upgrade_and_refresh_jobs_have_timeouts():
    data = _load()
    upgrade = data["resources"]["jobs"]["lakemeter_upgrade"]
    refresh = data["resources"]["jobs"]["lakemeter_pricing_refresh"]
    assert upgrade.get("max_concurrent_runs") == 1
    assert upgrade.get("timeout_seconds", 0) >= 3600
    assert refresh.get("timeout_seconds", 0) >= 1800
    assert refresh["schedule"]["pause_status"] == "PAUSED"


def test_jobs_have_notification_settings():
    data = _load()
    for key in ("lakemeter_installer", "lakemeter_upgrade", "lakemeter_pricing_refresh"):
        settings = data["resources"]["jobs"][key].get("notification_settings") or {}
        assert settings.get("no_alert_for_skipped_runs") is True
        assert settings.get("no_alert_for_canceled_runs") is True


def test_grants_helper_synced_in_bundle():
    data = _load()
    assert "lakebase_grants.py" in data["sync"]["include"]
