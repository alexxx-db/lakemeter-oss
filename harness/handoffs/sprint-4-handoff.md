# Sprint 4 Handoff: FMAPI_DATABRICKS + FMAPI_PROPRIETARY Parity

## What Was Built

### Bug Fixes (3 parity gaps fixed)

1. **`batch_inference` misclassification** — Backend treated `batch_inference` as provisioned/hourly, but frontend treats it as token-based (DBU per 1M tokens). Fixed in both `pricing.py` (`_is_fmapi_hourly`) and `excel_builder.py` (moved from provisioned check to token check). Affects 84 proprietary rate entries.

2. **FMAPI_DATABRICKS token fallback rates** — Backend was using proprietary-level fallbacks (21.43/321.43 for input/output) instead of matching frontend's Databricks-specific fallbacks (1.0/3.0). Added `FMAPI_DB_FALLBACK_RATES` dict in `excel_item_helpers.py`.

3. **FMAPI_DATABRICKS provisioned fallback rates** — Backend returned 0 when provisioned rate not found in JSON. Frontend falls back to 200 (scaling) / 50 (entry). Added `FMAPI_DB_PROVISIONED_FALLBACK` dict in `excel_item_helpers.py`.

### Files Modified
- `backend/app/routes/export/pricing.py` — Removed `batch_inference` from `_is_fmapi_hourly()`
- `backend/app/routes/export/excel_builder.py` — Added `batch_inference` to token-based check
- `backend/app/routes/export/excel_item_helpers.py` — Added Databricks-specific fallback rates for tokens and provisioned; updated `calc_item_values()` to select fallback based on workload type
- `tests/parity/test_parity_fmapi_databricks.py` — Expanded from 3 to 35 tests
- `tests/parity/test_parity_fmapi_proprietary.py` — Expanded from 4 to 39 tests

### Test Coverage (74 new FMAPI parity tests)

**FMAPI_DATABRICKS (35 tests):**
- 8 input_token tests (all LLM + embedding models: bge-large, gte, gemma, llama-3-1-8b, llama-3-3-70b, llama-4-maverick, gpt-oss-20b, gpt-oss-120b)
- 6 output_token tests (all LLMs with output rates)
- 8 provisioned tests (scaling + entry for multiple models, asymmetric rates, provisioned-only models llama-3-2-1b/3b)
- 6 SKU parametrized tests (all assert SERVERLESS_REAL_TIME_INFERENCE)
- 7 edge case tests (zero qty, unknown model fallbacks for input/output/provisioned_scaling/provisioned_entry, large qty)

**FMAPI_PROPRIETARY (39 tests):**
- 10 OpenAI tests (gpt-5, gpt-5-1, gpt-5-mini, gpt-5-nano across input/output/cache_read/cache_write/batch_inference, global + in_geo)
- 11 Anthropic tests (claude-sonnet-4-5, claude-haiku-4-5, claude-opus-4, claude-opus-4-1, claude-opus-4-5, claude-sonnet-4, claude-sonnet-3-7, claude-sonnet-4-1 across output/cache_read/cache_write/batch_inference, global + in_geo, short + long context)
- 6 Google tests (gemini-2-5-flash, gemini-2-5-pro across input/output, long + short context, global + in_geo)
- 3 SKU parametrized tests (OPENAI/ANTHROPIC/GEMINI_MODEL_SERVING)
- 7 edge case tests (zero qty, unknown model fallbacks for all token types, batch_inference regression, context_length fallback to 'all', large qty)
- 2 cross-provider comparison tests (different rates across providers, global vs in_geo pricing)

## How to Test
- `pytest tests/parity/test_parity_fmapi_databricks.py tests/parity/test_parity_fmapi_proprietary.py -v`
- `pytest tests/parity/ -v` — full parity regression (237 tests)

## Test Results
- `pytest tests/parity/` exit code: 0
- Tests: 237 passed (74 FMAPI + 163 prior workload tests)
- No regressions in any other workload type

## Known Limitations
- Fallback rates are hardcoded — if Databricks changes pricing, the fallbacks in both frontend and backend need to be updated in sync
- `batch_inference` for FMAPI_DATABRICKS does not exist in the pricing JSON (only proprietary has it), so no test for that specific combination
