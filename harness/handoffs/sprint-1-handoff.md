# Sprint 1 Handoff: Jobs (Classic + Serverless) — Iteration 4

## What Was Built

### Bug Fixes (This Iteration)
- **BUG-S1-12b**: Fixed `excel_row_writer.py` — `_write_vm_costs()` and `_write_total_costs()` had `nw = row_data.get('num_workers', 1)` defaulting to 1 worker. Changed to `default=0` to match frontend behavior. This ensures VM cost formulas don't inflate costs when `num_workers` is missing from row_data.

### Prior Iteration Fixes (Verified Still Working)
- **BUG-S1-5**: Serverless always applies photon 2x (built-in), regardless of `photon_enabled` flag
- **BUG-S1-6**: Lakebase formula corrected from `cu × nodes × 2` to `cu × nodes`
- **BUG-S1-12**: `calculations.py` uses `int(item.num_workers or 0)` (was `or 1`)
- **BUG-S1-13**: Hours fallback returns 0 when no usage data (was 11 hrs)
- **BUG-S1-15**: All Pydantic V2 deprecation warnings fixed (ConfigDict + SQLAlchemy orm import)

### Regression Tests Added (This Iteration)
- `TestBugS1_12b_ExcelRowWriterNumWorkersDefault` — 2 tests:
  - Verifies no `'num_workers', 1)` pattern in `excel_row_writer.py`
  - Scans all export modules for the same anti-pattern

## Files Changed (This Iteration)
- `backend/app/routes/export/excel_row_writer.py` — Lines 131, 154: `default=1` → `default=0`
- `tests/regression/test_sprint_1_bugs.py` — Added `TestBugS1_12b_ExcelRowWriterNumWorkersDefault` class (2 tests)

## How to Test
- **App URL**: https://lakemeter-e2e-v2-335310294452632.aws.databricksapps.com
- Create a Jobs line item with `num_workers=0` → export Excel → verify DBU/hr = driver-only (no worker contribution)
- Create a Jobs line item with no usage data → export Excel → verify $0 cost (not 11 hrs × rate)

## Test Results
```
Sprint 1 tests:     128 passed (tests/sprint_1/ — 6 test files)
Regression tests:    22 passed (tests/regression/test_sprint_1_bugs.py)
Sprint 1 total:     150 passed
Full suite total:   574 passed
Failures:             0
Warnings:             0
Duration:           3.60s
```

## Known Limitations
- **BUG-S1-9**: No Visual QA report exists — Visual QA Agent responsibility, not Build Agent
- **BUG-S1-11**: File size violations are pre-existing (ai_agent.py: 3822 lines, Calculator.tsx: 4106 lines) — out of scope for testing-only harness
