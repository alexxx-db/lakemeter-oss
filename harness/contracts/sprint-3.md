# Sprint 3 Contract: VECTOR_SEARCH + MODEL_SERVING + LAKEBASE Parity

## Acceptance Criteria

### Vector Search
- [ ] Standard mode: all capacity levels (1M, 2M, 3M, 5M, 10M, 50M) produce matching DBU/hr between frontend and backend
- [ ] Storage-optimized mode: all capacity levels (1M, 64M, 100M, 200M) produce matching DBU/hr
- [ ] CEILING math for unit calculation matches exactly (frontend `Math.ceil` vs backend `math.ceil`)
- [ ] Storage sub-row: free storage = units × 20 GB, billable = max(0, total - free), cost = billable × $0.023/GB
- [ ] Storage sub-row written correctly in Excel with proper DSU/GB notes
- [ ] SKU = SERVERLESS_REAL_TIME_INFERENCE for all Vector Search configs
- [ ] Monthly cost = DBU/hr × hours × $/DBU (within $0.01 tolerance)

### Model Serving
- [ ] CPU: DBU/hr matches (1.0 DBU/hr on AWS)
- [ ] GPU Small T4: DBU/hr matches (10.48 DBU/hr on AWS)
- [ ] GPU Medium A10G 1x: DBU/hr matches (20.0 DBU/hr on AWS)
- [ ] GPU Medium A10G 4x: DBU/hr matches (112.0 DBU/hr on AWS)
- [ ] GPU Medium A10G 8x: DBU/hr matches (290.8 DBU/hr on AWS)
- [ ] GPU XLarge A100 40GB 8x: DBU/hr matches (538.4 DBU/hr on AWS)
- [ ] GPU XLarge A100 80GB 8x: DBU/hr matches (628.0 DBU/hr on AWS)
- [ ] Case-insensitive GPU type lookup in backend
- [ ] SKU = SERVERLESS_REAL_TIME_INFERENCE for all Model Serving configs
- [ ] Monthly costs match within $0.01 tolerance

### Lakebase
- [ ] Basic CU computation: DBU/hr = CU × HA_nodes (tested at 1, 2, 4, 8, 16 CU)
- [ ] HA node multiplication correct for 1, 2, 3 nodes
- [ ] Storage DSU pricing: cost = GB × 15 DSU/GB × $0.023/DSU
- [ ] Storage sub-row in Excel has correct format and notes
- [ ] Edge cases: CU=0, storage=0, max storage (8192 GB)
- [ ] SKU = DATABASE_SERVERLESS_COMPUTE for all Lakebase configs
- [ ] Total cost = compute DBU cost + storage cost (within $0.01 tolerance)

## Test Plan

- Unit tests: Extend `tests/parity/test_parity_vector_search.py`, `test_parity_model_serving.py`, `test_parity_lakebase.py`
- Add `frontend_calc.py` helper for Vector Search storage cost
- Test storage sub-row values via `write_storage_subrow` function
- Regression: run full `pytest` including Sprint 1 and Sprint 2 tests

## Files Expected to Change

- `tests/parity/test_parity_vector_search.py` — new storage and edge case tests
- `tests/parity/test_parity_model_serving.py` — all GPU types + cost tests
- `tests/parity/test_parity_lakebase.py` — HA combos, storage edge cases, total cost
- `tests/parity/frontend_calc.py` — add `fe_vector_search_storage_cost` helper
- `backend/app/routes/export/excel_item_helpers.py` — fix if any mismatches found
- `backend/app/routes/export/calculations.py` — fix if any mismatches found
