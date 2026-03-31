# Sprint 1 Handoff (Iteration 3): Jobs (Classic + Serverless)

## What Was Fixed (Eval Iteration 2 → 3)

### BUG-S1-7: Empty test `test_serverless_rows_have_zero_vm` — FIXED
- **File**: `tests/sprint_1/test_jobs_export_integration.py:255-288`
- Replaced empty test body with real assertions:
  - Iterates over Excel rows, finds rows where column 3 (Mode) = "Serverless"
  - Asserts Driver VM $/Hr (col 22) is 0 or None
  - Asserts Worker VM $/Hr (col 23) is 0 or None
  - Asserts Total VM Cost (col 26) is 0 if numeric
  - Asserts at least 2 serverless rows found and checked
- **Verification**: Test passes — serverless rows correctly have zero VM costs

### BUG-S1-8: Coverage report not reproducible — FIXED
- **File**: `pyproject.toml`
- Added `[tool.coverage.run]`, `[tool.coverage.paths]`, `[tool.coverage.report]` sections
- Source path: `backend/app` with path mapping for module resolution
- **Verification**: `pytest --cov --cov-report=term-missing` produces clean, reproducible report

## Test Results

```
135 passed, 27 warnings in 2.10s
```

### Coverage (via `pytest tests/sprint_1/ --cov --cov-report=term-missing`)
- `backend/app/routes/export.py`: **63%** (Jobs paths only — Sprint 1 scope)
- `backend/app/routes/calculate.py`: 81%
- `backend/app/models/*`: 100%
- `backend/app/schemas/*`: 100%
- Overall app: 37%

## How to Test

- Run tests: `python3 -m pytest tests/ -v`
- Run with coverage: `python3 -m pytest tests/sprint_1/ --cov --cov-report=term-missing`
- Live app: https://lakemeter-e2e-v2-335310294452632.aws.databricksapps.com

## Files Changed

| File | Change |
|------|--------|
| `tests/sprint_1/test_jobs_export_integration.py` | Real assertions in `test_serverless_rows_have_zero_vm` (BUG-S1-7) |
| `pyproject.toml` | Coverage configuration (BUG-S1-8) |

## Known Limitations

- **BUG-S1-2**: No live browser testing — Visual QA Agent scope
- **BUG-S1-5 (pre-existing)**: Serverless photon 2x frontend/backend mismatch — documented, regression-tested
- **BUG-S1-6 (pre-existing)**: Lakebase DBU formula discrepancy — documented, regression-tested
- 27 warnings are pre-existing Pydantic V2 deprecation notices
