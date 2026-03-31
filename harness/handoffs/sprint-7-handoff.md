# Sprint 7 Handoff: FMAPI Proprietary (Anthropic, OpenAI, Google)

## What Was Built (Iteration 2 — Bug Fixes)

### Bug Fixes
1. **BUG-S7-1 (Critical)**: `excel_builder.py:131-135` — Added `cache_read`, `cache_write` to `is_fmapi_token` tuple; added `batch_inference` to `is_fmapi_provisioned` tuple. These rate types now route through the correct calculation paths instead of falling through to $0.

2. **BUG-S7-2 (Minor)**: `helpers.py:126-132` — Added display names for `cache_read` → "Cache Read", `cache_write` → "Cache Write", `batch_inference` → "Batch Inference" in the `rate_type_display` dict. Also updated `_fmapi_details` to show token quantity (not hours) for cache types.

3. **BUG-S7-3 (Minor)**: `pricing.py:159` — Added `batch_inference` to `_is_fmapi_hourly` check tuple.

4. **BUG-S7-4 (Minor)**: `pricing.py:113,143` — Both `_get_fmapi_sku` and `_get_fmapi_dbu_per_million` now use provider-aware defaults: Google defaults to `context='long'`, others default to `context='all'`.

5. **BUG-S7-6 (Minor)**: Extracted `_calc_item_values` and `_write_storage_subrow` into new `excel_item_helpers.py` (79 lines). `excel_builder.py` now 186 lines (under 200 limit).

### New Test Suite (BUG-S7-5)
Created `tests/sprint_7/` with 80 tests across 5 files:
- `test_fmapi_prop_sku_mapping.py` — Provider → SKU mapping (13 tests)
- `test_fmapi_prop_rates.py` — Rate type verification, cache/batch rates, endpoint variations (15 tests)
- `test_fmapi_prop_excel_export.py` — Excel export calculation paths for all rate types (17 tests)
- `test_fmapi_prop_edge_cases.py` — Google context, display names, file sizes (16 tests)
- `test_fmapi_prop_fe_be_alignment.py` — Frontend/backend cost alignment (19 tests)

## How to Test
- App URL: https://lakemeter-e2e-v2-335310294452632.aws.databricksapps.com
- Add FMAPI Proprietary line items with:
  - All 3 providers (Anthropic, OpenAI, Google)
  - All 5 rate types (input_token, output_token, cache_read, cache_write, batch_inference)
  - Both endpoint types (global, in_geo)
- Export to Excel → verify cache_read/cache_write/batch_inference produce non-zero costs
- Verify Google models resolve correctly with 'long' context length

## Test Results
- **Full suite**: 924/924 passed (4.42s)
- **Sprint 7 tests**: 80/80 passed (1.01s)
- **No regressions** from prior sprints (844 prior tests still pass)

## Files Changed
- `backend/app/routes/export/excel_builder.py` — Rate type tuples expanded, extracted helpers (186 lines)
- `backend/app/routes/export/excel_item_helpers.py` — NEW: extracted calc/storage functions (79 lines)
- `backend/app/routes/export/helpers.py` — Display names + token quantity for cache types
- `backend/app/routes/export/pricing.py` — batch_inference hourly check, Google context default
- `tests/sprint_7/__init__.py` — NEW
- `tests/sprint_7/conftest.py` — NEW: make_line_item fixture for FMAPI_PROPRIETARY
- `tests/sprint_7/fmapi_prop_calc_helpers.py` — NEW: shared calc helpers
- `tests/sprint_7/test_fmapi_prop_sku_mapping.py` — NEW: 13 tests
- `tests/sprint_7/test_fmapi_prop_rates.py` — NEW: 15 tests
- `tests/sprint_7/test_fmapi_prop_excel_export.py` — NEW: 17 tests
- `tests/sprint_7/test_fmapi_prop_edge_cases.py` — NEW: 16 tests
- `tests/sprint_7/test_fmapi_prop_fe_be_alignment.py` — NEW: 19 tests

## Known Limitations
- Google does not have cache_read/cache_write/batch_inference rate types in pricing JSON — SKU falls back to default for these (expected behavior, not a bug)
- FMAPI Proprietary does not have provisioned_scaling/provisioned_entry rate types — only batch_inference (hourly) and token-based types exist
