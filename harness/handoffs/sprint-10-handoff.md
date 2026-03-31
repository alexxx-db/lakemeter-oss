# Sprint 10 Handoff: Full Combined Estimate — Iteration 2

## What Was Built

101 tests verifying that all 9 workload types work correctly together in a single combined estimate with Excel export. Iteration 2 fixed all 4 bugs from evaluation and added 9 new tests.

### Iteration 2 Fixes

**BUG-S10-001 (Major)**: Model Serving GPU `gpu_medium` returned 0 DBU/hr
- Root cause: `gpu_medium` doesn't exist in pricing JSON; valid key is `gpu_medium_a10g_1x`
- Fix: `conftest.py` changed gpu type; test now asserts exact 20.0 DBU/hr with 0 warnings

**BUG-S10-003 (Minor)**: FMAPI SKU assertions too weak
- Fix: Replaced `isinstance(sku, str) and len(sku) > 0` with exact string matches: `SERVERLESS_REAL_TIME_INFERENCE` and `ANTHROPIC_MODEL_SERVING`

**BUG-S10-004 (Minor)**: `test_combined_excel.py` at 310 lines exceeded 200-line limit
- Split into: `test_excel_structure.py` (196 lines) + `test_excel_formulas.py` (154 lines)
- Also extracted: `test_cross_workload.py` (52 lines) + `test_pricing_lookups.py` (41 lines)
- All sprint 10 files now under 200 lines

**BUG-S10-002 (Minor)**: Notes column not tested
- Added `TestNotesColumn` in `test_excel_structure.py` with storage notes and non-empty assertions

**New**: `TestPricingLookups` (6 tests) verifying standard configs resolve without fallback warnings

### Files

| File | Lines | Action |
|------|-------|--------|
| `tests/sprint_10/conftest.py` | 173 | Modified — gpu_medium → gpu_medium_a10g_1x |
| `tests/sprint_10/test_combined_calc.py` | 177 | Modified — FMAPI SKU exact assertions, extracted classes |
| `tests/sprint_10/test_combined_excel.py` | — | Deleted — split into two files below |
| `tests/sprint_10/test_excel_structure.py` | 196 | New — structure/row/SKU/mode/hours/DBU/notes |
| `tests/sprint_10/test_excel_formulas.py` | 154 | New — formula/VM/token/NaN checks |
| `tests/sprint_10/test_cross_workload.py` | 52 | New — cross-workload consistency |
| `tests/sprint_10/test_pricing_lookups.py` | 41 | New — pricing fallback warning validation |
| `tests/sprint_10/test_combined_totals.py` | 196 | Unchanged |
| `tests/sprint_10/excel_helpers.py` | 127 | Unchanged |

## How to Test

```bash
cd "/Users/steven.tan/Desktop/Ent 1 - Q4 FY 2026 Team Project/lakemeter_app"
python -m pytest tests/sprint_10/ -v
```

## Test Results

- **Sprint 10**: 101 passed in 1.56s (up from 92)
- **Full suite (Sprints 1-10)**: 1254 passed in 5.81s (up from 1245)
- 0 failures, 0 errors

## Known Limitations

- DLT and Vector Search still use fallback pricing (backend data gap, not a test issue)
- 5 of 9 primary workload rows have Notes=None (backend export behavior; tests assert current state)
