# Sprint 1 Handoff: Jobs (Classic + Serverless) — Iteration 2 (Re-run)

## What Was Built / Fixed

This iteration verified and added regression tests for the two remaining discrepancies identified in the iteration 5 evaluation (7.90/10). Both bugs were already fixed in code from prior iterations.

### Bug Fixes Verified (Code Already Fixed)
1. **BUG-S1-12** (num_workers default): Backend `calculations.py:70` uses `int(item.num_workers or 0)` — aligned with frontend. Previously `or 1` caused Excel to overstate costs for zero-worker configs.
2. **BUG-S1-13** (hours fallback): Backend `calculations.py:22` returns `0` when no usage data — aligned with frontend. Previously returned 11 hours, causing non-zero Excel costs for $0 browser items.

### New Regression Tests Added
- `tests/regression/test_sprint_1_bugs.py`:
  - `TestBugS1_12_NumWorkersDefaultFixed` (3 tests): zero workers, None workers, frontend-backend agreement
  - `TestBugS1_13_HoursFallbackFixed` (3 tests): zero hours, zero cost, frontend-backend agreement

### Prior Fixes Still Verified (All Passing)
- **BUG-S1-5**: Serverless photon 2x always applied (3 regression tests)
- **BUG-S1-6**: Lakebase DBU formula cu × nodes (3 regression tests)
- **BUG-S1-1**: Shared fixture extracted to conftest.py (3 regression tests)
- **BUG-S1-3**: Integration test exists with endpoint tests (2 regression tests)

## Test Files

| File | Tests | Purpose |
|------|-------|---------|
| `tests/sprint_1/test_jobs_calculations.py` | 19 | Frontend/backend calc logic, all 4 configs |
| `tests/sprint_1/test_jobs_export.py` | 18 | Backend export helpers (_get_sku_type, etc.) |
| `tests/sprint_1/test_jobs_excel_export.py` | 20 | Excel formula verification with openpyxl |
| `tests/sprint_1/test_jobs_vm_and_notes.py` | 20 | VM costs, notes, NaN/$0 regression |
| `tests/sprint_1/test_jobs_discrepancies.py` | 7 | Frontend vs backend alignment verification |
| `tests/sprint_1/test_jobs_export_integration.py` | 10 | Real endpoint integration with TestClient |
| `tests/regression/test_sprint_1_bugs.py` | 17 | Regression tests for all 6 fixed bugs |

**Total Sprint 1 scope: 128 sprint tests + 17 regression tests = 145 tests**

## How to Test

```bash
# Run Sprint 1 tests only
cd "/Users/steven.tan/Desktop/Ent 1 - Q4 FY 2026 Team Project/lakemeter_app"
python -m pytest tests/sprint_1/ tests/regression/test_sprint_1_bugs.py -v

# Run full suite (all sprints)
python -m pytest tests/ -v
```

**Live app**: https://lakemeter-e2e-v2-335310294452632.aws.databricksapps.com

## Test Results

```
Sprint 1 + Regression: 145 passed, 0 failed, 11 warnings (1.82s)
Full suite (all sprints): 569 passed, 0 failed, 11 warnings (3.68s)
```

11 warnings are pre-existing (Pydantic V2 deprecation, SQLAlchemy declarative_base deprecation).

## Known Limitations

- **No Visual QA**: No live browser testing performed — Visual QA Agent responsibility
- **File size violations**: Pre-existing (ai_agent.py: 3,822 lines, Calculator.tsx: 4,106 lines) — out of scope for testing-only run
- **VM pricing**: Tests use hardcoded $0.20/$0.10 VM rates from export logic, not dynamic lookups

## Files Changed

| File | Change |
|------|--------|
| `harness/contracts/sprint-1.md` | Updated contract for iteration 2 with all acceptance criteria marked |
| `tests/regression/test_sprint_1_bugs.py` | Added 6 regression tests for BUG-S1-12 and BUG-S1-13 |
