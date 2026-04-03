# Sprint 1 Handoff: Excel Export SKU & Rate Alignment

## What Was Built

Fixed 7 bugs in the backend Excel export module to align SKU type mappings, fallback rates, photon multiplier logic, and FMAPI context defaults with the frontend UI:

- **Bug 1**: DLT Serverless SKU → `JOBS_SERVERLESS_COMPUTE` (was `DELTA_LIVE_TABLES_SERVERLESS`)
- **Bug 2**: FMAPI Proprietary context_length default → `'long'` for all providers (was `'all'` for non-Google)
- **Bug 3**: Added `_get_photon_multiplier()` reading from `dbu-multipliers.json` with warning on fallback (was hardcoded `*= 2`)
- **Bug 4/5**: Photon multiplier now uses actual JSON values (2.9 for AWS) instead of hardcoded 2.0
- **Bug 6**: FALLBACK_DBU_PRICES aligned: DLT_SERVERLESS 0.30 (was 0.50), Lakebase 0.48 (was 0.40)
- **Bug 7**: Removed `VECTOR_SEARCH_ENDPOINT`, added `DLT_*_(PHOTON)`, `GOOGLE_MODEL_SERVING`, `SERVERLESS_REAL_TIME_INFERENCE_LAUNCH`
- **VS Calc**: Vector Search units now use `math.ceil()` matching frontend

## Files Changed

### Backend (production code)
- `backend/app/routes/export/pricing.py` — SKU mappings, fallback prices, new `_get_photon_multiplier()`, `DBU_MULTIPLIERS` loader
- `backend/app/routes/export/calculations.py` — Photon multiplier from JSON, VS ceiling calc, gpu_type `.lower()`

### New Tests
- `tests/sprint_sku_alignment/` — 64 new tests: SKU resolution (33), fallback prices (24), FMAPI context (9), photon warning (2)

### Updated Tests
- `tests/regression/test_sprint_1_bugs.py` — Photon multiplier 2.0 → 2.9
- `tests/regression/test_sprint_3_bugs.py` — DLT SKU assertions aligned to fixed behavior
- `tests/sprint_1/test_jobs_export.py`, `test_jobs_excel_export.py` — Photon values
- `tests/sprint_3/test_dlt_export_calc.py`, `test_dlt_excel_export.py`, `test_dlt_export_sku.py`, `test_dlt_disc_pricing.py`, `test_dlt_excel_e2e_formulas.py` — DLT SKU + photon
- `tests/sprint_8/test_vs_dbu_calc.py`, `test_vs_edge_cases.py`, `test_vs_excel_compute.py`, `test_vs_excel_storage.py`, `test_vs_sku_pricing.py`, `vs_calc_helpers.py`, `excel_helpers.py` — VS ceiling + SKU
- `tests/sprint_9/test_lb_sku_pricing.py`, `test_lb_excel_storage.py` — Lakebase rates
- `tests/sprint_10/test_combined_calc.py`, `test_excel_structure.py`, `test_excel_formulas.py`, `test_regression_s10.py` — Combined fixes

## How to Test

```bash
cd /Users/steven.tan/Desktop/Ent\ 1\ -\ Q4\ FY\ 2026\ Team\ Project/lakemeter_app
source .venv/bin/activate
python -m pytest tests/ -q
```

## Test Results

- `pytest` exit code: 0
- Tests: **1714 passed**, 0 failed
- Duration: ~144s

## Known Limitations

- Photon multiplier values are cloud-specific (AWS=2.9, Azure=2.5). Tests only validate AWS.
- `DELTA_LIVE_TABLES_SERVERLESS` key remains in `FALLBACK_DBU_PRICES` for backward compatibility but is no longer returned by `_get_sku_type`.
