# Sprint 1 Contract: Excel Export — SKU & Rate Alignment

## Acceptance Criteria
- [ ] DLT Serverless returns `JOBS_SERVERLESS_COMPUTE` (not `DELTA_LIVE_TABLES_SERVERLESS`) from `_get_sku_type()`
- [ ] FMAPI Proprietary `_get_fmapi_sku()` defaults context_length to `'long'` for all providers (not `'all'` for non-Google)
- [ ] `FALLBACK_DBU_PRICES` matches frontend `DEFAULT_DBU_PRICING` for all shared entries
- [ ] `DELTA_LIVE_TABLES_SERVERLESS` fallback rate is $0.30 (was $0.50)
- [ ] `DATABASE_SERVERLESS_COMPUTE` fallback rate is $0.48 (was $0.40)
- [ ] `VECTOR_SEARCH_ENDPOINT` removed from fallbacks (unused by frontend)
- [ ] DLT photon entries added to fallbacks (`DLT_CORE_COMPUTE_(PHOTON)`, etc.)
- [ ] `GOOGLE_MODEL_SERVING` and `GEMINI_MODEL_SERVING` added to fallbacks at $0.07
- [ ] Photon multiplier fallback to 2.0 emits a warning
- [ ] Unit tests verify SKU resolution for all 9 workload types matches frontend logic
- [ ] Unit tests verify fallback price alignment between backend and frontend
- [ ] All existing tests still pass

## Test Plan
- Unit tests: SKU type resolution for each of the 9 workload types (JOBS, ALL_PURPOSE, DLT, DBSQL, VECTOR_SEARCH, MODEL_SERVING, FMAPI_DATABRICKS, FMAPI_PROPRIETARY, LAKEBASE) plus DATABRICKS_APPS
- Unit tests: Fallback DBU price parity between backend `FALLBACK_DBU_PRICES` and frontend `DEFAULT_DBU_PRICING`
- Unit tests: FMAPI context_length default behavior
- Unit tests: Photon multiplier warning on fallback
- Regression: All existing sprint 1-11 tests must pass
