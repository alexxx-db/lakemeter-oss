# Sprint 1 Contract: Automated Parity Test Framework

## Acceptance Criteria
- [ ] Parametrized pytest suite covering all 9 workload types with min 3 scenarios each
- [ ] Each test verifies: DBU/hr, $/DBU price, monthly DBU cost, storage cost (where applicable), total monthly cost
- [ ] Tests load real pricing data from `backend/static/pricing/*.json`
- [ ] Any parity mismatch produces a clear diff showing expected vs actual values
- [ ] All tests pass (0 failures)
- [ ] Minimum 27 test cases (9 types x 3 scenarios)
- [ ] Tests replicate frontend costCalculation.ts logic in Python for comparison

## Test Plan

### Test file: `tests/parity/test_parity_all_workloads.py`
Parametrized test suite with one module per workload type section:

1. **JOBS** (3+ scenarios): classic, serverless standard, serverless performance + photon
2. **ALL_PURPOSE** (3+ scenarios): classic, photon, serverless (always performance mode)
3. **DLT** (3+ scenarios): Core classic, Pro photon, Advanced serverless
4. **DBSQL** (3+ scenarios): Classic Small, Pro Medium, Serverless 4X-Large
5. **VECTOR_SEARCH** (3+ scenarios): standard 1M, standard 5M, storage_optimized 100M
6. **MODEL_SERVING** (3+ scenarios): cpu, gpu_small_t4, gpu_medium_a10g_1x
7. **FMAPI_DATABRICKS** (3+ scenarios): input_token, output_token, provisioned_scaling
8. **FMAPI_PROPRIETARY** (3+ scenarios): openai input, anthropic output, google input
9. **LAKEBASE** (3+ scenarios): basic CU, HA nodes, with storage

### Helper: `tests/parity/frontend_calc.py`
Python reimplementation of frontend costCalculation.ts formulas for comparison.

### Verification per test case:
- `dbu_per_hour` (backend `_calculate_dbu_per_hour` vs frontend formula)
- `dbu_price` (backend `_get_dbu_price` vs frontend `dbuRatesMap` lookup)
- `monthly_dbus` (dbu/hr × hours or tokens × rate)
- `monthly_dbu_cost` (monthly_dbus × dbu_price)
- `storage_cost` (for LAKEBASE and VECTOR_SEARCH)
- `total_monthly_cost` (dbu_cost + storage_cost + vm_cost)

## Production Readiness Items This Sprint
- Test infrastructure only — no production code changes
