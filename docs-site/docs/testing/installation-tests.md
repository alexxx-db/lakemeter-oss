---
sidebar_position: 13
---

# Installation Validation Tests

The installation test suite (`tests/test_installation/`) validates the Lakemeter installer packaging, pricing data, and app configuration without requiring network access.

The supported installer path is **`scripts/install.sh` + `scripts/databricks.yml`** (Databricks Asset Bundles on serverless). Legacy `scripts/install_lakemeter.py` may still exist for reference but is not the primary install path.

## Test Files

### `test_installer_script.py`

Static analysis of the active installer packaging (`install.sh`, DAB notebooks, shared helpers).

| Test area | What it checks |
|-----------|----------------|
| Script presence | `install.sh` and required notebooks exist |
| DAB graph | Installer tasks, dependencies, and serverless environments |
| Grants | Least-privilege helper is synced and used |
| Critical patterns | Lakebase OAuth SP identity, SSL connections, CSV pricing load |

### `test_pricing_data.py`

Validates pricing artifacts used by the installer. Active installs load **CSV** files staged into the DAB `pricing_data/` sync path (from `backend/static/pricing` / conversion scripts). JSON files under `backend/static/pricing/` remain useful for local parity tests and frontend bundles.

### `test_app_config.py`

Validates root `app.yaml` Databricks App configuration:

| Test area | What it checks |
|-----------|----------------|
| YAML validity | File parses as valid YAML |
| Command | Starts uvicorn for the FastAPI app |
| `valueFrom` references | Lakebase project/branch/endpoint and DB bindings |
| Hardcoded values | `ENVIRONMENT=production`, `DB_PORT`, `DB_SSLMODE` |

Related contract tests outside this folder:

- `tests/test_dab_config.py` — targets, timeouts, concurrency, paused pricing refresh
- `tests/test_lakebase_grants.py` — least-privilege SQL grants
- `tests/test_pricing_freshness.py` — freshness metadata + API

## Running the Tests

```bash
cd "/path/to/lakemeter-oss"

python -m pytest tests/test_installation/ tests/test_dab_config.py \
  tests/test_lakebase_grants.py tests/test_pricing_freshness.py -q
```

## Hosting vs estimated clouds

- **Estimated clouds** in the product UI: AWS, Azure, and GCP pricing models.
- **Hosting**: Databricks Apps + Lakebase Autoscaling today target AWS and Azure workspaces. Install Lakemeter in an AWS/Azure workspace even when sizing a GCP estimate.
