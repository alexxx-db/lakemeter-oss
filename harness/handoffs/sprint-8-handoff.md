# Sprint 8 Handoff: Vector Search (Standard + Storage Optimized)

## What Was Built

112 new tests covering Vector Search calculation verification across 5 test files:

### Test Files
| File | Tests | Coverage |
|------|-------|----------|
| `tests/sprint_8/test_vs_dbu_calc.py` | 34 | DBU/hr calc: standard (2M/unit, 4.0 DBU), storage optimized (64M/unit, 18.29 DBU), monthly DBUs, all 3 clouds, zero/none capacity, helper alignment |
| `tests/sprint_8/test_vs_sku_pricing.py` | 20 | SKU = VECTOR_SEARCH_ENDPOINT, $/DBU lookup ($0.088 fallback), serverless classification, rates JSON validation (6 keys, divisors, rates) |
| `tests/sprint_8/test_vs_excel_export.py` | 19 | Compute row formula (=P*L), storage sub-row emission, DATABRICKS_STORAGE SKU, storage GB approximation, storage cost, totals SUM, serverless markers, DBU/hr values, no NaN |
| `tests/sprint_8/test_vs_edge_cases.py` | 24 | Config display (mode + capacity), fractional capacity (0.1M–1.5M), large capacity (1000M–10000M), default mode (None → standard), no negatives, calc_item_values integration, run-based hours, display name |
| `tests/sprint_8/test_vs_config_display.py` | 15 | Mode display variations, capacity text for 1/2/10/64/100M, zero/null capacity omission, separator logic, full pipeline tests |

### Supporting Files
| File | Purpose |
|------|---------|
| `tests/sprint_8/conftest.py` | `make_line_item()` fixture factory for VECTOR_SEARCH defaults |
| `tests/sprint_8/vs_calc_helpers.py` | Calculation helpers: `calc_dbu_per_hour()`, `calc_units()`, `calc_monthly_dbus()`, `calc_storage_gb()`, `get_all_cloud_mode_combos()` |

## How to Test
```bash
cd lakemeter_app && source .venv/bin/activate
# Sprint 8 only
pytest tests/sprint_8/ -v
# Full suite
pytest tests/ -v
```

## Test Results
- Sprint 8: **112 passed** in 1.91s
- Full suite: **1036 passed** in 5.58s (924 prior + 112 new)
- 0 failures, 0 errors

## Acceptance Criteria Status
All 20 acceptance criteria from contract covered:
- AC-1 to AC-5: DBU calculation — PASS (34 tests)
- AC-6 to AC-8: SKU & pricing — PASS (20 tests)
- AC-9 to AC-14: Excel export — PASS (19 tests)
- AC-15 to AC-16: Config display — PASS (15 tests)
- AC-17 to AC-20: Edge cases — PASS (24 tests)

## Key Findings
1. **Backend uses division, not CEIL**: `units = capacity * 1M / divisor` — NOT `ceil()` as spec suggested. This means fractional units are valid (e.g., 5M / 2M = 2.5 units).
2. **Storage GB approximation**: 1M vectors ≈ 1 GB (used in storage sub-row).
3. **All 3 clouds have identical rates**: aws, azure, gcp all use 4.0/18.29 DBU rates.
4. **Empty mode defaults to standard**: Backend uses `mode or 'standard'`.

## Files Changed
```
tests/sprint_8/conftest.py               (new)
tests/sprint_8/vs_calc_helpers.py         (new)
tests/sprint_8/test_vs_dbu_calc.py        (new)
tests/sprint_8/test_vs_sku_pricing.py     (new)
tests/sprint_8/test_vs_excel_export.py    (new)
tests/sprint_8/test_vs_edge_cases.py      (new)
tests/sprint_8/test_vs_config_display.py  (new)
harness/contracts/sprint-8.md             (new)
harness/state.json                        (updated)
```
