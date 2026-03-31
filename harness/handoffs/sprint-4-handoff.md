# Sprint 4 Handoff: DBSQL (Classic, Pro, Serverless — All Sizes) — Iteration 2

## What Was Built (Iteration 2 Fixes)

Fixed 2 bugs from Sprint 4 evaluation + added missing run-based hours test.

### Bug Fixes
- **BUG-S4-1**: `_calc_dbsql_dbu` now clamps negative/zero cluster counts to 1 via `max(1, int(...))` — previously negative clusters produced negative DBU values
- **BUG-S4-2**: Empty or whitespace-only warehouse size now triggers a warning ("Empty warehouse size, defaulting to Small") instead of silently defaulting

### New Tests
- `tests/regression/test_sprint_4_bugs.py` — 8 regression tests for BUG-S4-1 and BUG-S4-2
- `tests/sprint_4/test_dbsql_calculations.py` — 2 new run-based hours tests (10 runs/day × 30 min × 22 days = 110 hrs, verified FE + BE)

### Updated Tests
- `tests/sprint_4/test_dbsql_vm_and_notes.py` — Updated `test_empty_string_size` and `test_negative_clusters` to match new behavior

## How to Test
- Run: `python3 -m pytest tests/ -v`
- Live app: https://lakemeter-e2e-v2-335310294452632.aws.databricksapps.com
- Navigate to Calculator → add DBSQL line items (Classic Small, Pro Medium 2-cluster, Serverless Large, Serverless 4X-Large)

## Test Results
- `pytest` exit code: 0
- Tests: 709 total (10 new), 0 failures
- All sprint 4 files under 200 lines

## Files Changed
- `backend/app/routes/export/calculations.py` — `_calc_dbsql_dbu`: added `max(1,...)` guard + empty string warning
- `tests/regression/test_sprint_4_bugs.py` — NEW: 8 regression tests
- `tests/sprint_4/test_dbsql_calculations.py` — Added 2 run-based hours tests
- `tests/sprint_4/test_dbsql_vm_and_notes.py` — Updated 2 edge case tests for new behavior

## Known Limitations
- VM pricing for Classic/Pro DBSQL uses default estimates ($0.20/$0.10), not real instance prices
- Live app UI verification still needed (Visual QA scope)
