# Sprint 8 Handoff: Vector Search (Standard + Storage Optimized) — Iteration 2

## What Was Built

118 tests (up from 112) covering Vector Search calculation verification across 5 test files.

### Iteration 2 Changes (from evaluator feedback)

1. **Bug fix — negative capacity clamp**: Backend `_calc_vector_search_dbu()` now clamps capacity to `max(0, ...)` so negative values produce 0 DBU/hr instead of negative costs.
2. **6 new negative capacity tests**: `test_negative_capacity_clamps_to_zero` (3 parametrized: -5, -1, -0.1) and `test_negative_capacity_units_non_negative` (3 parametrized) in `TestNoNegatives`.
3. **Removed sys.path.insert boilerplate**: Added `__init__.py` to `tests/sprint_8/` and `pythonpath = ["backend"]` to `pyproject.toml`, removing the `sys.path.insert` hack from all 5 test files.

### Test Files
| File | Tests | Coverage |
|------|-------|----------|
| `tests/sprint_8/test_vs_dbu_calc.py` | 34 | DBU/hr calc: standard (2M/unit, 4.0 DBU), storage optimized (64M/unit, 18.29 DBU), monthly DBUs, all 3 clouds, zero/none capacity, helper alignment |
| `tests/sprint_8/test_vs_sku_pricing.py` | 20 | SKU = VECTOR_SEARCH_ENDPOINT, $/DBU lookup ($0.088 fallback), serverless classification, rates JSON validation (6 keys, divisors, rates) |
| `tests/sprint_8/test_vs_excel_export.py` | 19 | Compute row formula (=P*L), storage sub-row emission, DATABRICKS_STORAGE SKU, storage GB approximation, storage cost, totals SUM, serverless markers, DBU/hr values, no NaN |
| `tests/sprint_8/test_vs_edge_cases.py` | 30 | Config display (mode + capacity), fractional capacity (0.1M–1.5M), large capacity (1000M–10000M), default mode (None → standard), no negatives (incl. -5/-1/-0.1), calc_item_values integration, run-based hours, display name |
| `tests/sprint_8/test_vs_config_display.py` | 15 | Mode display variations, capacity text for 1/2/10/64/100M, zero/null capacity omission, separator logic, full pipeline tests |

### Supporting Files
| File | Purpose |
|------|---------|
| `tests/sprint_8/__init__.py` | Package marker (new — enables pythonpath config) |
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
- Sprint 8: **118 passed** in 1.94s
- Full suite: **1042 passed** in 4.67s (924 prior + 118 new)
- 0 failures, 0 errors

## Acceptance Criteria Status
All 20 acceptance criteria from contract covered:
- AC-1 to AC-5: DBU calculation — PASS (34 tests)
- AC-6 to AC-8: SKU & pricing — PASS (20 tests)
- AC-9 to AC-14: Excel export — PASS (19 tests)
- AC-15 to AC-16: Config display — PASS (15 tests)
- AC-17 to AC-20: Edge cases — PASS (30 tests, +6 negative capacity)

## Files Changed (Iteration 2)
```
backend/app/routes/export/calculations.py  (modified — negative capacity clamp)
tests/sprint_8/__init__.py                 (new — package marker)
tests/sprint_8/test_vs_edge_cases.py       (modified — 6 new negative capacity tests, removed sys.path.insert)
tests/sprint_8/test_vs_dbu_calc.py         (modified — removed sys.path.insert)
tests/sprint_8/test_vs_sku_pricing.py      (modified — removed sys.path.insert)
tests/sprint_8/test_vs_excel_export.py     (modified — removed sys.path.insert)
tests/sprint_8/test_vs_config_display.py   (modified — removed sys.path.insert)
pyproject.toml                             (modified — added pythonpath = ["backend"])
harness/state.json                         (updated)
```
