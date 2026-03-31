# Sprint 1 Handoff (Iteration 4): Jobs (Classic + Serverless)

## What Was Fixed (Eval Iteration 3 → 4)

### BUG-S1-5: Serverless Photon Frontend/Backend Mismatch — FIXED
- **File**: `backend/app/routes/export.py` lines 330-334
- **Root cause**: Backend only applied photon 2x for serverless when `photon_enabled=True`. Databricks serverless compute has photon built-in — it should always apply.
- **Fix**: Moved serverless check before photon check. Serverless now always gets `base_dbu *= 2` regardless of `photon_enabled` flag.
- **Impact**: Excel exports now match browser-displayed costs for serverless Jobs. Previously understated by 2x.
- **Tests updated**: `test_jobs_export.py`, `test_jobs_calculations.py`, `test_jobs_discrepancies.py`, `tests/regression/test_sprint_1_bugs.py`

### BUG-S1-6: Lakebase DBU Formula Discrepancy — FIXED
- **File**: `backend/app/routes/export.py` line 381
- **Root cause**: Backend used `cu * nodes * 2` but correct formula is `cu * nodes` (matching frontend and Databricks docs).
- **Fix**: Removed erroneous `* 2` multiplier: `return cu * nodes, warnings`
- **Impact**: Excel exports now show correct Lakebase compute costs. Previously overstated by 2x.
- **Tests updated**: `test_jobs_vm_and_notes.py`, `tests/regression/test_sprint_1_bugs.py`

### BUG-S1-10: Handoff Test Count Clarity — FIXED
- Sprint 1 tests: **132** (in `tests/sprint_1/`)
- Regression tests: **7** (in `tests/regression/test_sprint_1_bugs.py`, expanded from original 7 to cover new fix assertions)
- **Total: 139 tests passing**

## Test Results

```
139 passed, 27 warnings in 1.77s
  - 132 tests in tests/sprint_1/ (4 updated for new behavior)
  - 7 regression test classes in tests/regression/ (expanded with new assertions)
```

27 warnings are pre-existing (Pydantic V2 deprecation, datetime.utcnow deprecation).

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
| `backend/app/routes/export.py` | BUG-S1-5: Serverless always applies photon 2x; BUG-S1-6: Lakebase formula fixed to `cu × nodes` |
| `tests/sprint_1/test_jobs_export.py` | Updated serverless tests for photon-always-on behavior |
| `tests/sprint_1/test_jobs_calculations.py` | Updated `backend_calc_jobs` helper + discrepancy test → alignment test |
| `tests/sprint_1/test_jobs_discrepancies.py` | Discrepancy #1 now verifies FE/BE alignment (not discrepancy) |
| `tests/sprint_1/test_jobs_vm_and_notes.py` | Lakebase formula tests updated to `cu × nodes` |
| `tests/regression/test_sprint_1_bugs.py` | BUG-S1-5 and S1-6 regression tests now verify fixes (not document discrepancies) |

## Known Limitations

- **BUG-S1-9**: No live browser testing — Visual QA Agent scope
- **BUG-S1-11**: File modularity violations (pre-existing, out of scope for testing sprint)
- **Discrepancy #2** (num_workers default): Frontend defaults to 0, backend to 1 — still exists, documented
- **Discrepancy #3** (hours fallback): Frontend returns 0, backend returns 11 hours — still exists, documented
- 27 warnings are pre-existing Pydantic V2 deprecation notices
