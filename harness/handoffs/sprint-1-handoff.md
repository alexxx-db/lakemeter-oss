# Sprint 1 Handoff: JOBS + ALL_PURPOSE Parity (Iteration 2)

## What Was Built

### Iteration 1 (prior)
1. **Driver DBU fallback rate** (`calculations.py:56`): Changed from 0.25 to 0.5 to match frontend
2. **Vector Search storage sub-row AttributeError** (`excel_builder.py:183`): Safe getattr
3. **9 new tests** (Excel e2e + edge cases)
4. **Sprint 10 test expected values** updated for correct 0.5 driver fallback

### Iteration 2 Fixes (this iteration)
Fixed all 11 test failures from iteration 1 evaluation:

**1. Driver DBU Fallback Warning Message (1 file)**
- `calculations.py:69` — Warning said "using 0.25" but actual fallback is 0.5. Fixed message.

**2. Fallback DBU Test Expectations (3 test files)**
- `tests/sprint_1/test_jobs_export.py` — Updated `test_fallback_dbu_rates_when_no_instance`: driver=0.5, total=1.5
- `tests/sprint_2/test_allpurpose_export.py` — Updated `test_unknown_instance_type_warning`: total=2.5
- `tests/sprint_3/test_dlt_export_calc.py` — Updated `test_unknown_instance_warning`: total=2.5

**3. Vector Search Storage Sub-Row Tests (3 test files)**
- `tests/sprint_8/conftest.py` — Added `vector_search_storage_gb` to defaults
- `tests/sprint_8/test_vs_excel_storage.py` — All 6 storage tests now set `vector_search_storage_gb > 0` (required by both frontend and backend for storage row emission)
- `tests/sprint_10/conftest.py` — Added `vector_search_storage_gb=50` to `make_vector_search_standard()`, added field to `make_line_item`

**4. Row Count & Notes Tests (3 test files)**
- `tests/sprint_10/test_excel_structure.py` — Row count 10→11 (VS storage sub-row)
- `tests/sprint_10/test_combined_totals.py` — VS storage test expects sub-row; row counts 10→11
- Sprint 11 notes test now passes (VS storage sub-row provides needed notes rows)

## How to Test
- Start: `cd backend && uvicorn app.main:app --reload --port 8000`
- Run tests: `python -m pytest tests/ --tb=short`

## Test Results
- `pytest` exit code: 0
- Tests: 1762 passed, 0 failed
- Duration: ~147s

## Files Changed (Iteration 2)
- `backend/app/routes/export/calculations.py` — Fixed warning message (0.25→0.5)
- `tests/sprint_1/test_jobs_export.py` — Fixed fallback expectations
- `tests/sprint_2/test_allpurpose_export.py` — Fixed fallback expectations
- `tests/sprint_3/test_dlt_export_calc.py` — Fixed fallback expectations
- `tests/sprint_8/conftest.py` — Added vector_search_storage_gb default
- `tests/sprint_8/test_vs_excel_storage.py` — Set vector_search_storage_gb in test items
- `tests/sprint_10/conftest.py` — Added vector_search_storage_gb to VS fixture + defaults
- `tests/sprint_10/test_combined_totals.py` — Updated VS storage + row count expectations
- `tests/sprint_10/test_excel_structure.py` — Updated row count expectations

## Known Limitations
- VM costs are always $0 in Excel export (intentional — frontend loads VM pricing on-demand)
