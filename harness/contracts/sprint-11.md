# Sprint 11 Contract: Model Serving Re-validation + Sprint 10 Regression Tests

## Context

Sprint 5 (Model Serving) passed at 9.38/10 but Sprint 10 (Full Combined Estimate) iteration 1 scored 8.10/10 due to 4 bugs. Those bugs were fixed in Sprint 10 iteration 2, which scored 9.0+. This sprint adds explicit regression tests to guard against recurrence and strengthens Model Serving validation in the combined estimate context.

## Acceptance Criteria

### Regression Tests for BUG-S10-001 through BUG-S10-004

- [ ] AC-1: Regression test that `gpu_medium` (bare, invalid key) returns 0 DBU/hr with a warning
- [ ] AC-2: Regression test that `gpu_medium_a10g_1x` (valid key) returns 20.0 DBU/hr with no warnings
- [ ] AC-3: Regression test that FMAPI Databricks SKU is exactly `SERVERLESS_REAL_TIME_INFERENCE` (not just non-empty)
- [ ] AC-4: Regression test that FMAPI Proprietary (Anthropic) SKU is exactly `ANTHROPIC_MODEL_SERVING`
- [ ] AC-5: Regression test that all Sprint 10 test files are under 200 lines
- [ ] AC-6: Regression test that notes column has correct behavior: items with fallback pricing have notes, items without user notes and no warnings have empty notes

### Model Serving in Combined Estimate Validation

- [ ] AC-7: Model Serving GPU (A10G 1x) in combined estimate produces non-zero DBU cost
- [ ] AC-8: Model Serving row in Excel has exact SKU `SERVERLESS_REAL_TIME_INFERENCE`
- [ ] AC-9: Model Serving row in Excel has DBU/Hr = 20.0
- [ ] AC-10: Model Serving row in Excel has formula for DBUs/Mo (not static value)
- [ ] AC-11: Model Serving row in Excel has no VM costs (serverless)
- [ ] AC-12: All 14 GPU types across 3 clouds produce correct DBU/hr rates (parametrized)

### Notes Column Completeness

- [ ] AC-13: Storage sub-rows (Lakebase, Vector Search) always have notes
- [ ] AC-14: Items with fallback pricing warnings have auto-generated notes
- [ ] AC-15: Notes behavior is documented: no-user-notes + no-warnings = empty notes (expected)

## Test Plan

- Regression tests: `tests/sprint_11/test_regression_s10_bugs.py`
- Model Serving combined validation: `tests/sprint_11/test_ms_combined_validation.py`
- Notes column: `tests/sprint_11/test_notes_completeness.py`
- Shared helpers: reuse `tests/sprint_10/excel_helpers.py` and `tests/sprint_10/conftest.py`

## File Size Limit

All test files must be under 200 lines.
