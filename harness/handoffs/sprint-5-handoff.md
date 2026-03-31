# Sprint 5 Handoff: Model Serving (All GPU Types)

## What Was Built

Testing-only sprint — Model Serving calculation verification tests and Excel export validation across all GPU types and clouds.

### Bug Found & Fixed
- **BUG-S5-1**: `gpu_medium_g2_standard_8` (GCP GPU) missing from `MODEL_SERVING_GPU_NAMES` in `backend/app/routes/export/helpers.py`. Added display name "Medium (G2 Standard 8)".

### Test Files (all Sprint 5)
| File | Lines | Tests | Purpose |
|------|-------|-------|---------|
| `conftest.py` | 44 | — | `make_line_item` fixture for MODEL_SERVING |
| `ms_calc_helpers.py` | 104 | — | Shared FE/BE calc functions, GPU rates |
| `test_ms_gpu_rates.py` | 108 | 25 | All GPU types × 3 clouds, FE/BE match |
| `test_ms_sku_pricing.py` | 64 | 9 | SKU mapping, pricing, serverless detection |
| `test_ms_export_calc.py` | 146 | 18 | Backend calc functions, hours, monthly cost |
| `test_ms_config_display.py` | 93 | 9 | GPU display names, config details format |
| `test_ms_excel_export.py` | 173 | 10 | Real .xlsx: SKU, formulas, totals, mode label |
| `test_ms_edge_cases.py` | 139 | 54 | NaN guards, zero hours, cross-cloud, FE/BE alignment |

## How to Test

```bash
cd "/Users/steven.tan/Desktop/Ent 1 - Q4 FY 2026 Team Project/lakemeter_app"
# Sprint 5 tests only
python3 -m pytest tests/sprint_5/ -v
# Full suite
python3 -m pytest tests/ -v
```

## Test Results

- Sprint 5: **125 passed** in 1.39s
- Full suite: **699 passed** in 3.52s
- Failures: 0
- Regressions: 0

## Acceptance Criteria Status

| AC | Status | Notes |
|----|--------|-------|
| AC-1 to AC-12 | PASS | All GPU rates verified across AWS/Azure/GCP |
| AC-13 | PASS | SKU = SERVERLESS_REAL_TIME_INFERENCE for all |
| AC-14 | PASS | $/DBU = $0.07 fallback |
| AC-15, AC-16 | PASS | Always serverless, no VM costs |
| AC-17 to AC-19 | PASS | Hours calculation (direct, run-based, priority) |
| AC-20 to AC-22 | PASS | Monthly DBUs, DBU cost, total cost |
| AC-23, AC-24 | PASS | GPU display names (fixed GCP G2 bug) |
| AC-25 to AC-28 | PASS | Excel SKU, formulas, totals, serverless label |
| AC-29 to AC-32 | PASS | Edge cases, NaN guards |

**Summary**: 32/32 PASS

## File Size Compliance

| File | Lines | Status |
|------|-------|--------|
| conftest.py | 44 | PASS |
| ms_calc_helpers.py | 104 | PASS |
| test_ms_gpu_rates.py | 108 | PASS |
| test_ms_sku_pricing.py | 64 | PASS |
| test_ms_export_calc.py | 146 | PASS |
| test_ms_config_display.py | 93 | PASS |
| test_ms_excel_export.py | 173 | PASS |
| test_ms_edge_cases.py | 139 | PASS |

**8/8 PASS** — all files ≤200 lines

## Known Limitations
- Frontend uses fallback of 2 DBU/hr for unknown GPU types; backend returns 0. This is a documented FE/BE difference, not a bug.
- No live browser testing performed (per testing-only mode).

## Files Changed
- `tests/sprint_5/` — 9 new test files (125 tests)
- `backend/app/routes/export/helpers.py` — added `gpu_medium_g2_standard_8` to GPU names
