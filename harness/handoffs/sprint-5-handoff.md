# Sprint 5 Handoff: Cross-Workload Regression + Excel Formula Audit

## What Was Built

### Excel Formula Audit (Manual Code Review)
- Audited ALL formula cells in `excel_row_writer.py` and `excel_sections.py`
- Verified 9 distinct formula patterns: DBUs/Mo (token & hourly), DBU Rate Disc, DBU Cost List/Disc, VM costs (driver/worker/total), Total Cost List/Disc
- Verified totals row SUM formulas span full data range including storage sub-rows
- Verified cost summary section: Monthly references totals row, Annual = Monthly × 12
- Verified DBU summary uses same SUM range as totals
- **Result: All formulas are correct — no fixes needed**

### Cross-Workload Regression Tests (`tests/sprint_5_regression/`)
Three new test files with 104 tests total:

1. **`test_regression_all_workloads.py`** (71 tests) — Multi-config regression for all 9 workload types:
   - JOBS: classic, photon, serverless standard, serverless performance (verified perf = 2× std)
   - ALL_PURPOSE: classic, photon, serverless
   - DLT: Core classic, Pro serverless, Advanced photon
   - DBSQL: Classic/Small, Pro/Medium, Serverless/Large
   - MODEL_SERVING: CPU, GPU A10G
   - FMAPI_DATABRICKS: input tokens, output tokens, batch inference, provisioned
   - FMAPI_PROPRIETARY: OpenAI input, Anthropic output, Google input
   - VECTOR_SEARCH: standard, storage-optimized
   - LAKEBASE: 2CU/1HA, 8CU/3HA
   - Cross-workload validation: all 26 items valid DBU, SKU, hours, $/DBU price
   - Cross-cloud regression: aws, azure, gcp (all valid)

2. **`test_formula_values.py`** (11 tests) — Excel formula pattern verification for the full 26-item estimate:
   - DBUs/Mo formulas: token items use N*O, hourly items use P*L
   - DBU Rate Disc: R*(1-S)
   - DBU Cost List: Q*R, DBU Cost Disc: Q*T
   - VM cost formulas: driver W*L, worker X*L*I, total Y+Z
   - Total Cost List: U+AA, Total Cost Disc: V+AA
   - No NaN, #REF!, #VALUE!, float NaN, or Inf in any data cell

3. **`test_cost_summary.py`** (22 tests) — Totals, cost summary, and DBU summary:
   - Totals row exists, positioned after all data rows
   - SUM formulas span first-to-last data row (parametrized for all 8 summed columns)
   - Storage sub-rows within SUM range
   - Cost summary: Monthly references totals row, Annual = Monthly × 12
   - DBU summary formula matches totals range
   - Cross-cloud: all 3 clouds generate correct row counts and totals
   - Edge cases: empty estimates, single-item estimates

## How to Test
- Run: `pytest tests/sprint_5_regression/ -v` (104 tests)
- Run: `pytest tests/ -q` (full suite: 2055 tests)

## Test Results
- `pytest` exit code: 0
- Tests: 2055 passed (1951 existing + 104 new)
- Coverage: all 9 workload types × multiple configurations × 3 clouds

## Known Limitations
- openpyxl reads formulas as strings (not evaluated values), so formula verification checks formula patterns rather than computing results. The cached values written by xlsxwriter are verified indirectly through the calculation unit tests.

## Files Changed
- `harness/contracts/sprint-5.md` — sprint contract
- `tests/sprint_5_regression/__init__.py` — new test package
- `tests/sprint_5_regression/conftest.py` — 26 multi-config workload fixtures
- `tests/sprint_5_regression/excel_helpers.py` — Excel generation and inspection helpers
- `tests/sprint_5_regression/test_regression_all_workloads.py` — 71 regression tests
- `tests/sprint_5_regression/test_formula_values.py` — 11 formula verification tests
- `tests/sprint_5_regression/test_cost_summary.py` — 22 totals/summary tests
