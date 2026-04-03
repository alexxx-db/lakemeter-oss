# Sprint 1 Contract: Installation Testing

## Feature
Validate `scripts/install_lakemeter.py` installer and all artifacts it produces — pricing data, app.yaml config, SP role configuration, database schema. Pure local tests (no network calls).

## Acceptance Criteria

### Installer Script Validation
- [ ] Installer script exists and is parseable Python
- [ ] All 9 step functions are defined and callable
- [ ] `--skip-provision`, `--profile`, `--skip-deploy` CLI args supported
- [ ] SP role creation uses `identity_type: SERVICE_PRINCIPAL` (not PG_ONLY)
- [ ] DB connections use `sslmode=require`

### Pricing Data Validation (Step 5)
- [ ] All 9 pricing JSON files exist in `backend/static/pricing/`
- [ ] Each file is valid JSON with > 0 entries
- [ ] manifest.json lists all 9 files with total_entries > 0
- [ ] DBU rates keys use `cloud:region:tier` format
- [ ] Instance DBU rates keys use `cloud:instance_type` format
- [ ] DBSQL rates, multipliers, FMAPI rates all have correct key formats

### App Config Validation (Step 9)
- [ ] `app.yaml` is valid YAML
- [ ] Contains 5 `valueFrom` references
- [ ] Contains hardcoded values for ENVIRONMENT, DB_PORT, DB_SSLMODE
- [ ] Command starts uvicorn on port 8000

### Installer Code Quality
- [ ] Pricing loader uses TRUNCATE + batch insert pattern
- [ ] All step functions have docstrings
- [ ] Error handling present (sys.exit on critical failures)

## Test Plan
- Static tests: installer script parsing, function signatures, code pattern verification
- Data tests: pricing JSON schema/format/content validation
- Config tests: app.yaml structure and valueFrom pattern
- All tests pass with `pytest tests/test_installation/ -v`

## Files to Create
- `tests/test_installation/__init__.py`
- `tests/test_installation/test_installer_script.py`
- `tests/test_installation/test_pricing_data.py`
- `tests/test_installation/test_app_config.py`
