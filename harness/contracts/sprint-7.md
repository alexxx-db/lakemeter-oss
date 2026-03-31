# Sprint 7 Contract: FMAPI Proprietary (Anthropic, OpenAI, Google)

## Acceptance Criteria
- [x] AC-1: Each provider maps to correct SKU ({PROVIDER}_MODEL_SERVING)
- [x] AC-2: Google correctly maps to GEMINI_MODEL_SERVING (not GOOGLE_)
- [x] AC-3: cache_read, cache_write rate types have distinct rates
- [x] AC-4: Excel token formula columns populated correctly for ALL rate types (input_token, output_token, cache_read, cache_write, batch_inference)
- [x] AC-5: Different endpoint types (global/in_geo) show different rates
- [x] AC-6: Frontend/backend cost alignment for all rate types across all 3 providers

## Bug Fixes (from iteration 1 evaluation)
- [x] BUG-S7-1 (Critical): Excel export produces $0 for cache_read, cache_write, batch_inference
- [x] BUG-S7-2 (Minor): Missing display names for cache/batch rate types
- [x] BUG-S7-3 (Minor): _is_fmapi_hourly doesn't include batch_inference
- [x] BUG-S7-4 (Minor): Google context_length defaults to 'all' instead of 'long'
- [x] BUG-S7-5 (Major): No Sprint 7 tests
- [x] BUG-S7-6 (Minor): excel_builder.py exceeds 200-line limit

## Test Plan
- Provider → SKU mapping for all 3 providers × input/output
- cache_read/cache_write distinct rates and backend lookup
- batch_inference hourly classification and calculation
- Global vs in_geo endpoint rate differences
- All providers × all clouds rate existence
- calc_item_values for all 5 rate types (non-zero DBUs)
- Display names for all 7 rate types
- File size limits for export modules
- Frontend/backend cost alignment across providers
