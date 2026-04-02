# Sprint 10 Handoff (Iteration 2): Combined Estimate + AI Multi-Workload Tests

## What Was Built (Iteration 2 — Evaluator Fixes)

Addressed all 4 bugs from sprint-10-eval.md (score 8.10 → targeting 9.5+):

### BUG-S10-001: Model Serving GPU pricing
- **Already resolved in iter 1**: conftest uses `gpu_medium_a10g_1x` (not `gpu_medium`), test asserts 20.0 DBU/hr
- **Iter 2 addition**: 4 regression tests in `test_regression_s10.py::TestBugS10001ModelServingGpu` — validates GPU type name, non-zero DBU/hr, no warnings, and Excel output

### BUG-S10-002: Notes column for fallback-pricing items
- **New test**: `test_excel_structure.py::TestNotesColumn::test_warning_items_have_notes` — asserts DLT and Vector Search rows have non-empty notes
- **4 regression tests** in `test_regression_s10.py::TestBugS10002FallbackNotesInExcel` — checks fallback note content, SKU mention, and that non-fallback items don't have warnings

### BUG-S10-003: FMAPI SKU assertions
- **Already resolved in iter 1**: exact string assertions (`SERVERLESS_REAL_TIME_INFERENCE`, `ANTHROPIC_MODEL_SERVING`)
- **3 regression tests** in `test_regression_s10.py::TestBugS10003FmapiSkuExact` — exact match + differ check

### BUG-S10-004: File size compliance
- **Already resolved in iter 1**: split into `test_excel_structure.py` + `test_excel_formulas.py`
- **1 regression test** in `test_regression_s10.py::TestBugS10004FileSizeCompliance` — scans all sprint 10 test files, asserts ≤200 lines

### Additional improvements
- **Expanded `test_pricing_lookups.py`**: Added `TestFallbackPricingExpected` (DLT, FMAPI DB, FMAPI Prop behavior) and `TestMultiCloudPricing` (cross-cloud validation for Jobs, DBSQL, Model Serving)

## Files Created

| File | Lines | Purpose |
|------|-------|---------|
| `tests/sprint_10/test_regression_s10.py` | 141 | Regression tests for BUG-S10-001..004 (12 tests) |

## Files Modified

| File | Lines | Change |
|------|-------|--------|
| `tests/sprint_10/test_excel_structure.py` | 193 | Added `test_warning_items_have_notes` |
| `tests/sprint_10/test_pricing_lookups.py` | 96 | Added fallback pricing + multi-cloud test classes |

## How to Test

```bash
cd lakemeter_app
source .venv/bin/activate

# Sprint 10 tests only
pytest tests/sprint_10/ -v

# Full regression (non-AI)
pytest --ignore=tests/ai_assistant -v

# AI assistant tests (requires FMAPI access)
pytest tests/ai_assistant/sprint_10/ -v --timeout=300
```

## Test Results

- **Sprint 10 tests**: 119 passed, 0 failed (1.45s) — up from 101 in iter 1 (+18 tests)
- **Full regression**: 1405 passed, 0 failed (6.82s)
- **AI assistant tests**: 62 collected (require live FMAPI, not run in build phase)
- **All files under 200 lines**: verified by `TestBugS10004FileSizeCompliance`

## Known Limitations

- DLT (`DELTA_LIVE_TABLES_SERVERLESS`) and Vector Search (`VECTOR_SEARCH_ENDPOINT`) SKUs use fallback pricing — these are real pricing data gaps, not test issues
- Model Serving `gpu_medium_a10g_1x` resolves on AWS only; Azure/GCP may have different GPU type names
- AI assistant tests are non-deterministic due to LLM responses
