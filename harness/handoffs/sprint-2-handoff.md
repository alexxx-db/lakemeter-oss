# Sprint 2 Handoff (Iteration 2): All-Purpose (Classic + Serverless)

## What Was Built

### Iteration 1 (99 tests)
99 tests across 6 files covering All-Purpose workload calculations, export, discrepancies, VM costs, and integration.

### Iteration 2 (fixes + 12 new tests)
**3 backend code fixes** in `export.py` + **10 new regression tests** + **updated 8 existing tests** to reflect fixed behavior.

#### Backend Fixes
1. **BUG-S1-12 FIXED**: `export.py:327` — `num_workers` default changed from `or 1` to `or 0` (aligned with frontend)
2. **BUG-S1-13 FIXED**: `export.py:301` — Hours fallback changed from 11 hrs to 0 (aligned with frontend)
3. **BUG-S2-1 FIXED**: `export.py:333` — ALL_PURPOSE Serverless now always uses performance mode (2x), matching frontend behavior
4. **Secondary fix**: `export.py:905` — Second `num_workers or 1` in VM costs section also changed to `or 0`

#### Regression Tests Added
- `tests/regression/test_sprint_2_bugs.py` — 10 new tests:
  - `TestBugS1_12_NumWorkersDefaultFixed` (3 tests): 0 workers = driver only for JOBS and ALL_PURPOSE
  - `TestBugS1_13_HoursFallbackFixed` (3 tests): no usage data = 0 hours
  - `TestBugS2_1_AllPurposeServerlessModeFixed` (4 tests): ALL_PURPOSE serverless always 2x, Jobs still respects mode

#### Updated Tests
Sprint 1 and Sprint 2 tests that asserted the old (broken) behavior updated to assert the fixed behavior:
- `test_jobs_calculations.py`: `backend_calc_jobs` replica updated, discrepancy tests now assert alignment
- `test_jobs_discrepancies.py`: Discrepancy #2 and #3 tests now verify FE/BE alignment
- `test_jobs_export.py`: `test_default_num_workers` and `test_fallback_when_nothing_set` updated
- `test_allpurpose_calculations.py`: `backend_calc_allpurpose` replica updated
- `test_allpurpose_discrepancies.py`: All 3 discrepancy classes now verify alignment (not discrepancy)
- `test_allpurpose_export.py`: serverless mode, num_workers default, hours fallback tests updated

## How to Test

```bash
# Run full suite (Sprint 1 + Sprint 2 + Regression)
cd "/Users/steven.tan/Desktop/Ent 1 - Q4 FY 2026 Team Project/lakemeter_app"
python -m pytest tests/ -v

# Run Sprint 2 only
python -m pytest tests/sprint_2/ -v

# Run regression tests only
python -m pytest tests/regression/ -v
```

## Test Results

```
250 passed, 0 failed, 51 warnings
  - Sprint 1: 128 tests
  - Sprint 2: 101 tests (99 iter1 + 2 new alignment tests)
  - Regression: 21 tests (11 Sprint 1 + 10 Sprint 2)
```

## Files Changed

### Backend (code fixes)
- `backend/app/routes/export.py` — 3 fixes (num_workers default, hours fallback, ALL_PURPOSE serverless mode)

### Tests (new)
- `tests/regression/test_sprint_2_bugs.py` — 10 new regression tests

### Tests (updated)
- `tests/sprint_1/test_jobs_calculations.py` — backend_calc_jobs replica updated
- `tests/sprint_1/test_jobs_discrepancies.py` — discrepancy tests now verify alignment
- `tests/sprint_1/test_jobs_export.py` — num_workers and hours fallback tests updated
- `tests/sprint_2/test_allpurpose_calculations.py` — backend_calc_allpurpose replica updated
- `tests/sprint_2/test_allpurpose_discrepancies.py` — all discrepancy tests now verify alignment
- `tests/sprint_2/test_allpurpose_export.py` — serverless mode, num_workers, hours tests updated

## Known Limitations
- VM cost values in tests use hardcoded $0.20/$0.10 (matching backend export.py) — actual VM pricing is more complex
- No browser E2E tests — those are for Visual QA agent
- The 3 backend fixes affect ALL workload types that use these code paths (Jobs, DLT), not just All-Purpose
