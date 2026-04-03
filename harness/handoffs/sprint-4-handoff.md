# Sprint 4 Handoff: FMAPI_DATABRICKS + FMAPI_PROPRIETARY Parity

## What Was Built (Iteration 1)

### Bug Fixes (3 parity gaps fixed)

1. **`batch_inference` misclassification** — Backend treated `batch_inference` as provisioned/hourly, but frontend treats it as token-based (DBU per 1M tokens). Fixed in both `pricing.py` (`_is_fmapi_hourly`) and `excel_builder.py` (moved from provisioned check to token check). Affects 84 proprietary rate entries.

2. **FMAPI_DATABRICKS token fallback rates** — Backend was using proprietary-level fallbacks (21.43/321.43 for input/output) instead of matching frontend's Databricks-specific fallbacks (1.0/3.0). Added `FMAPI_DB_FALLBACK_RATES` dict in `excel_item_helpers.py`.

3. **FMAPI_DATABRICKS provisioned fallback rates** — Backend returned 0 when provisioned rate not found in JSON. Frontend falls back to 200 (scaling) / 50 (entry). Added `FMAPI_DB_PROVISIONED_FALLBACK` dict in `excel_item_helpers.py`.

### Test Coverage (74 new FMAPI parity tests)

**FMAPI_DATABRICKS (35 tests):**
- 8 input_token tests (all LLM + embedding models)
- 6 output_token tests (all LLMs with output rates)
- 8 provisioned tests (scaling + entry for multiple models)
- 6 SKU parametrized tests (all assert SERVERLESS_REAL_TIME_INFERENCE)
- 7 edge case tests (zero qty, unknown model fallbacks, large qty)

**FMAPI_PROPRIETARY (39 tests):**
- 10 OpenAI tests (gpt-5 family across all rate types, endpoints)
- 11 Anthropic tests (claude models across all rate types, contexts)
- 6 Google tests (gemini models across input/output, contexts)
- 3 SKU parametrized tests (OPENAI/ANTHROPIC/GEMINI_MODEL_SERVING)
- 7 edge case tests (zero qty, fallbacks, batch_inference regression)
- 2 cross-provider comparison tests

## What Was Fixed (Iteration 2)

1. **Sprint 7 test `test_batch_inference_is_hourly`** — Incorrectly asserted `_is_fmapi_hourly` returns True for batch_inference. Frontend only treats `provisioned_scaling` as provisioned. Fixed to assert False.

2. **Sprint 7 test `test_batch_inference_produces_nonzero_dbus`** — Was passing `is_fmapi_provisioned=True` for batch_inference. Fixed to use `is_fmapi_token=True, is_fmapi_provisioned=False` matching real code path.

3. **File size limit** — `pricing.py` was 204 lines (max 200). Compacted dict entries and docstrings to exactly 200.

### Files Modified (Iteration 2)
- `backend/app/routes/export/pricing.py` — compacted to 200 lines
- `tests/sprint_7/test_fmapi_prop_excel_export.py` — fixed batch_inference tests
- `tests/sprint_7/test_fmapi_prop_rates.py` — updated docstring

## How to Test
- Start: `cd backend && uvicorn app.main:app --reload --port 8000`
- Test FMAPI workloads: various models × rate types → export to Excel → compare
- `pytest tests/parity/ -v` — full parity regression (237 tests)

## Test Results
- `pytest` exit code: 0
- Tests: 1951 passed, 0 failed
- Duration: ~2.5 minutes

## Known Limitations
- Fallback rates are hardcoded — if Databricks changes pricing, both frontend and backend need sync
- `batch_inference` for FMAPI_DATABRICKS does not exist in pricing JSON (only proprietary has it)
