# Sprint 1 Handoff: Installation Testing

## What Was Built

### Test Suite: `tests/test_installation/` (91 tests, 3 files)

**`test_installer_script.py`** (21 tests) — Static analysis of `scripts/install_lakemeter.py`:
- Script exists and is parseable Python
- All 10 step functions defined with docstrings
- CLI args: `--profile`, `--skip-provision`, `--skip-deploy`
- Critical patterns: `identity_type=SERVICE_PRINCIPAL`, SSL connections, TRUNCATE before insert
- Roles API URL pattern, DATABRICKS_SUPERUSER membership
- All 12 helper functions exist
- Constants: `lakemeter_pricing`, `DEFAULT_SCHEMA`, `TOTAL_STEPS = 9`

**`test_pricing_data.py`** (49 tests) — Validates all 9 pricing JSON files:
- All files exist and are valid JSON with entries
- manifest.json lists all 9 files with positive total_entries
- DBU rates: `cloud:region:tier` key format, valid clouds
- Instance DBU rates: top-level cloud keys, entries have dbu_rate > 0 and vcpus
- DBSQL rates: `cloud:type:size` format, dbu_per_hour > 0
- Multipliers: `cloud:type:feature` format, multiplier > 0
- FMAPI (Databricks + proprietary): `cloud:model:rate_type` format
- Model serving and vector search: entries present, key format valid

**`test_app_config.py`** (21 tests) — Validates `app.yaml`:
- Valid YAML, command runs uvicorn on 0.0.0.0:8000 via bash
- 5 valueFrom references match expected resource names
- Hardcoded values: ENVIRONMENT=production, DB_PORT=5432, DB_SSLMODE=require
- DATABRICKS_HOST uses `{{databricks_host}}` template
- SP credential keys (SP_CLIENT_ID_KEY, SP_SECRET_KEY) present

## How to Test

```bash
cd "/Users/steven.tan/Desktop/Ent 1 - Q4 FY 2026 Team Project/lakemeter_app"
source .venv/bin/activate
python -m pytest tests/test_installation/ -v
```

No network connectivity required — all tests are local/static.

## Test Results

- **91 tests passed**, 0 failed
- Runtime: 0.16s
- No network dependencies (pure local validation)

## Known Limitations

- Tests validate installer code structure and data files statically — they do NOT execute the installer against a live Lakebase instance (that's Sprint 2's scope)
- Pricing data format tests check first N entries per file, not exhaustive full-file validation

## Files Created

- `tests/test_installation/__init__.py`
- `tests/test_installation/test_installer_script.py` (21 tests)
- `tests/test_installation/test_pricing_data.py` (49 tests)
- `tests/test_installation/test_app_config.py` (21 tests)
- `harness/contracts/sprint-1.md` (updated for new spec)
