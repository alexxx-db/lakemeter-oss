# Sprint 5 Contract: Cross-Workload Regression + Excel Formula Audit

## Acceptance Criteria

### AC-1: Full Regression Sweep (All 9 Workload Types × Multiple Configs)
- [ ] Every workload type tested with at least 2 configurations (classic/photon/serverless variants)
- [ ] JOBS: classic, photon, serverless standard, serverless performance
- [ ] ALL_PURPOSE: classic, photon, serverless
- [ ] DLT: Core/Pro/Advanced × classic/serverless
- [ ] DBSQL: Classic/Pro/Serverless × multiple sizes
- [ ] MODEL_SERVING: CPU, GPU small, GPU medium
- [ ] FMAPI_DATABRICKS: input tokens, output tokens, batch inference, provisioned
- [ ] FMAPI_PROPRIETARY: OpenAI/Anthropic/Google × input/output tokens
- [ ] VECTOR_SEARCH: standard, storage-optimized (with and without storage)
- [ ] LAKEBASE: various CU sizes and HA node counts
- [ ] All DBU/hr, hours, total DBU, $/DBU, and total cost calculations verified

### AC-2: Excel Formula Value Verification
- [ ] Every formula cell's cached value matches the formula's expected result
- [ ] DBUs/Mo formula: token items =N*O, hourly items =P*L — cached value matches
- [ ] DBU Rate (Disc.) formula: =R*(1-S) — cached value matches
- [ ] DBU Cost (List) formula: =Q*R — cached value matches
- [ ] DBU Cost (Disc.) formula: =Q*T — cached value matches
- [ ] Driver VM Total: =W*L — cached value matches
- [ ] Worker VM Total: =X*L*I — cached value matches
- [ ] Total VM: =Y+Z — cached value matches
- [ ] Total Cost (List): =U+AA — cached value matches
- [ ] Total Cost (Disc.): =V+AA — cached value matches

### AC-3: Totals Row SUM Formula Verification
- [ ] Totals row SUM range spans ALL data rows including storage sub-rows
- [ ] SUM of DBUs/Mo, DBU Cost List, DBU Cost Disc, VM costs, Total costs verified
- [ ] Sum of cached data row values equals the totals row cached value (within $0.01)

### AC-4: Cost Summary Section Verification
- [ ] Monthly row references correct totals row cells
- [ ] Annual row = Monthly × 12 for every column
- [ ] DBU summary total matches totals row DBUs/Mo

### AC-5: Cross-Cloud Regression
- [ ] All 9 workload types produce valid results for aws, azure, gcp
- [ ] No NaN, #REF!, or broken values in any cloud configuration

### AC-6: All Existing Tests Pass
- [ ] Full `pytest tests/` suite passes with 0 failures

## Test Plan

- New test file: `tests/sprint_5/test_regression_all_workloads.py` — multi-config regression
- New test file: `tests/sprint_5/test_formula_values.py` — formula cached value verification
- New test file: `tests/sprint_5/test_cost_summary.py` — cost summary and totals verification
- Run existing `tests/parity/` and `tests/sprint_10/` as regression baseline
