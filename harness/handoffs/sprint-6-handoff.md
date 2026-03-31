# Sprint 6 Handoff: FMAPI Databricks (Token + Provisioned)

## What Was Built

135 tests covering FMAPI_DATABRICKS workload type across all calculation paths:

### Test Files (8 files, all ≤200 lines)
| File | Tests | Purpose |
|------|-------|---------|
| conftest.py | - | Shared `make_line_item()` fixture |
| fmapi_db_calc_helpers.py | - | FE/BE calculation replication + rate lookups |
| test_fmapi_db_rates.py | 43 | Token + provisioned rate lookups, cross-cloud, JSON validation |
| test_fmapi_db_sku_pricing.py | 19 | SKU mapping, fallback pricing, serverless detection, DBU/hr=0 |
| test_fmapi_db_export_calc.py | 18 | Token/provisioned DBU calculation, FE/BE alignment |
| test_fmapi_db_config_display.py | 12 | Display name, config details, rate type labels |
| test_fmapi_db_excel_export.py | 12 | Real .xlsx generation: formulas, token columns, SKU, totals |
| test_fmapi_db_edge_cases.py | 31 | Unknown model, zero qty, NaN guards, output>input, entry≤scaling |

### Models Tested (10 unique models × 3 clouds)
- LLMs: llama-3-3-70b, llama-3-1-8b, llama-3-2-1b, llama-3-2-3b, llama-4-maverick, gpt-oss-20b, gpt-oss-120b, gemma-3-12b
- Embeddings: bge-large, gte
- Rate types: input_token, output_token, provisioned_scaling, provisioned_entry

### Key Verifications
- Token-based: `monthly_dbus = quantity_M × dbu_per_1M_tokens`
- Provisioned: `monthly_dbus = hours × dbu_per_hour`
- Output rate > input rate for all models with both
- provisioned_entry ≤ provisioned_scaling for all models
- Cross-cloud rates identical for same model
- Excel: token formula (=N*O) for token items, hours formula for provisioned
- No NaN/Inf for any valid model+rate_type combination

## How to Test
```bash
cd "/Users/steven.tan/Desktop/Ent 1 - Q4 FY 2026 Team Project/lakemeter_app"
python3 -m pytest tests/sprint_6/ -v
```

## Test Results
- Sprint 6 tests: **135 passed**
- Full suite: **844 passed, 0 failures**
- Runtime: 3.97s

## Acceptance Criteria Status
All 34 acceptance criteria PASS (AC-1 through AC-34).

## Known Limitations
- GCP llama-3-1-8b provisioned rates differ from AWS/Azure (106.0 vs 53.571 for entry) — this matches the pricing JSON, may need data verification
- Frontend fallback defaults (200 DBU/hr for provisioned_scaling, 50 for entry) differ from backend (0 for unknown) — by design, FE provides UX defaults

## Files Changed
- `tests/sprint_6/__init__.py` (new)
- `tests/sprint_6/conftest.py` (new)
- `tests/sprint_6/fmapi_db_calc_helpers.py` (new)
- `tests/sprint_6/test_fmapi_db_rates.py` (new)
- `tests/sprint_6/test_fmapi_db_sku_pricing.py` (new)
- `tests/sprint_6/test_fmapi_db_export_calc.py` (new)
- `tests/sprint_6/test_fmapi_db_config_display.py` (new)
- `tests/sprint_6/test_fmapi_db_excel_export.py` (new)
- `tests/sprint_6/test_fmapi_db_edge_cases.py` (new)
- `harness/contracts/sprint-6.md` (new)
- `harness/state.json` (updated)
