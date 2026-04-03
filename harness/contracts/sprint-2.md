# Sprint 2 Contract: Integration & Regression Testing

## Acceptance Criteria

- [ ] AC-1: Full pytest suite runs — 1419+ original tests pass (excluding network-dependent skips)
- [ ] AC-2: 91 installation tests from Sprint 1 still pass (no regressions)
- [ ] AC-3: 10 Lakebase permission tests exist and are properly skip-guarded for offline runs
- [ ] AC-4: Integration test: SP OAuth flow verified (token gen → DB connect → query execution)
- [ ] AC-5: Integration test: App health endpoint returns 200
- [ ] AC-6: Cross-workload regression: all 9 workload types have tests (JOBS, ALL_PURPOSE, DLT, DBSQL, MODEL_SERVING, VECTOR_SEARCH, FMAPI_DATABRICKS, FMAPI_PROPRIETARY, LAKEBASE)
- [ ] AC-7: Multi-workload scenarios pass (sprint 10-11 test suites)
- [ ] AC-8: AI assistant tests pass (sprint_1, sprint_2 AI tests) or are skip-guarded
- [ ] AC-9: All regression tests pass (tests/regression/)
- [ ] AC-10: New integration test file validates cross-feature data consistency
- [ ] AC-11: Test summary report generated showing pass/fail/skip counts per module

## Test Plan

- Run `pytest` on the full suite with `-v --tb=short`
- Create `tests/test_integration_validation/` with:
  - `test_suite_completeness.py`: validates all expected test modules exist and collect
  - `test_workload_coverage.py`: verifies each of the 9 workload types has test coverage
  - `test_permission_flow.py`: integration test for SP OAuth flow (skip-guarded)
  - `test_cross_feature_consistency.py`: validates pricing data consistency across workloads
- Run tests in isolation groups to identify any cross-contamination

## Files

- `tests/test_integration_validation/__init__.py`
- `tests/test_integration_validation/test_suite_completeness.py`
- `tests/test_integration_validation/test_workload_coverage.py`
- `tests/test_integration_validation/test_permission_flow.py`
- `tests/test_integration_validation/test_cross_feature_consistency.py`

## Production Readiness Items This Sprint
- N/A (testing-only validation sprint)
