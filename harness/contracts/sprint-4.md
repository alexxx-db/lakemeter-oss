# Sprint 4 Contract: FMAPI_DATABRICKS + FMAPI_PROPRIETARY Parity

## Acceptance Criteria

### Bug Fixes
- [ ] `batch_inference` rate type for FMAPI_PROPRIETARY must be treated as token-based (not provisioned/hourly) — matching frontend behavior
- [ ] FMAPI_DATABRICKS token-based fallback rates must match frontend: input_token=1.0, output_token=3.0 (not proprietary-level 21.43/321.43)
- [ ] FMAPI_DATABRICKS provisioned fallback rates must match frontend: provisioned_scaling=200, provisioned_entry=50 (not 0)

### Parity Verification
- [ ] All FMAPI_DATABRICKS rate types tested: input_token, output_token, provisioned_scaling, provisioned_entry
- [ ] All FMAPI_PROPRIETARY providers tested: openai, anthropic, google
- [ ] All FMAPI_PROPRIETARY rate types tested: input_token, output_token, cache_read, cache_write, batch_inference
- [ ] SKU assignment verified: SERVERLESS_REAL_TIME_INFERENCE (Databricks), OPENAI/ANTHROPIC/GEMINI_MODEL_SERVING (Proprietary)
- [ ] Frontend fallback paths produce identical results to backend fallback paths
- [ ] Endpoint type (global, in_geo) and context length (all, short, long) correctly propagated

### Test Coverage
- [ ] Comprehensive FMAPI_DATABRICKS parity tests covering all 10 models × token types + provisioned modes
- [ ] Comprehensive FMAPI_PROPRIETARY parity tests covering all 3 providers × models × rate types × endpoint types × context lengths
- [ ] Fallback rate tests for when pricing data is missing
- [ ] Edge cases: zero quantity, embedding models (input-only), provisioned-only models

## Files to Modify
- `backend/app/routes/export/pricing.py` — fix `_is_fmapi_hourly`, add FMAPI_DATABRICKS fallbacks
- `backend/app/routes/export/excel_item_helpers.py` — fix fallback rate selection for Databricks vs Proprietary
- `backend/app/routes/export/excel_builder.py` — add `batch_inference` to token-based check
- `tests/parity/test_parity_fmapi_databricks.py` — expand tests
- `tests/parity/test_parity_fmapi_proprietary.py` — expand tests

## Test Plan
- Run `pytest tests/parity/test_parity_fmapi_databricks.py tests/parity/test_parity_fmapi_proprietary.py -v`
- Run `pytest tests/parity/ -v` for full parity regression
- Run `pytest` for full suite regression
