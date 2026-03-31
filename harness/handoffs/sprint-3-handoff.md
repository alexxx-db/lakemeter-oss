# Sprint 3 Handoff: DLT (Classic + Serverless, All Editions)

## What Was Built

### Test Files Created (5 files, 133 new tests)
- `tests/sprint_3/__init__.py` — Package init
- `tests/sprint_3/conftest.py` — DLT-specific `make_line_item` fixture
- `tests/sprint_3/test_dlt_calculations.py` — Frontend calculation logic replicated in Python (36 tests)
  - Hours calculation (run-based, direct, priority, defaults)
  - DLT Core/Pro/Advanced Classic Standard
  - DLT Classic Photon (all 3 editions)
  - DLT Serverless Standard and Performance
  - Edge cases (0 workers, large cluster, parametric hours)
- `tests/sprint_3/test_dlt_export.py` — Backend export function tests (28 tests)
  - `_get_sku_type` for all DLT variants
  - `_calculate_dbu_per_hour` for all modes
  - `_calculate_hours_per_month`, `_is_serverless_workload`
  - DBU price lookup for all DLT SKUs
- `tests/sprint_3/test_dlt_discrepancies.py` — FE vs BE alignment tests (35 tests)
  - Classic Standard: ALIGNED (all editions)
  - Classic Photon: DISCREPANCY (BE missing _(PHOTON) suffix)
  - Serverless SKU: DISCREPANCY (FE=JOBS_SERVERLESS, BE=DELTA_LIVE_TABLES)
  - Serverless pricing: DISCREPANCY ($0.39 vs $0.50)
  - Full SKU alignment matrix (9 combinations)
- `tests/sprint_3/test_dlt_excel_export.py` — Excel export pipeline tests (22 tests)
  - Display name and config details
  - Full calculation pipeline (hours → DBU → cost)
  - 3 editions × 4 modes matrix (12 parametrized tests)
- `tests/regression/test_sprint_3_bugs.py` — Regression guards (12 tests)
  - BUG-S3-1: DLT Serverless SKU (documented)
  - BUG-S3-2: DLT Photon SKU suffix (documented)
  - BUG-S3-3: DLT mode respected (standard vs performance)

### Contract
- `harness/contracts/sprint-3.md` — 30 acceptance criteria

## How to Test

```bash
# Run Sprint 3 tests only
cd "/Users/steven.tan/Desktop/Ent 1 - Q4 FY 2026 Team Project/lakemeter_app"
python -m pytest tests/sprint_3/ tests/regression/test_sprint_3_bugs.py -v

# Run full suite (including Sprint 1+2 regression)
python -m pytest tests/ -v
```

## Test Results

- Sprint 3 tests: **133 passed** in 0.96s
- Full suite: **386 passed** in 2.39s
- Failures: 0
- Regressions: 0

## Key Findings: 3 Frontend/Backend Discrepancies

### DISCREPANCY 1: DLT Serverless SKU (HIGH IMPACT)
- **Frontend**: `JOBS_SERVERLESS_COMPUTE` — uses Jobs Serverless pricing ($0.39/DBU)
- **Backend**: `DELTA_LIVE_TABLES_SERVERLESS` — uses DLT-specific pricing ($0.50/DBU)
- **Impact**: Excel export shows 28% higher cost than browser for DLT Serverless
- **Example**: 4 workers, 730 hrs: Browser=$2,847, Excel=$3,650, Delta=$803/mo

### DISCREPANCY 2: DLT Classic Photon SKU Suffix (MEDIUM IMPACT)
- **Frontend**: `DLT_{EDITION}_COMPUTE_(PHOTON)` (e.g., `DLT_CORE_COMPUTE_(PHOTON)`)
- **Backend**: `DLT_{EDITION}_COMPUTE` (no `_(PHOTON)` suffix)
- **Impact**: Excel SKU column differs from browser; may affect price lookup if photon-specific rates exist

### DISCREPANCY 3: DLT Serverless $/DBU Rate (MEDIUM IMPACT)
- **Frontend fallback**: $0.30 (DELTA_LIVE_TABLES_SERVERLESS) or $0.39 (JOBS_SERVERLESS)
- **Backend fallback**: $0.50 (DELTA_LIVE_TABLES_SERVERLESS)
- **Root cause**: Different SKU mappings lead to different price lookups

## Known Limitations
- Tests verify calculation logic only (no live browser interaction — that's Visual QA)
- Backend DLT Photon SKU and Serverless SKU discrepancies are DOCUMENTED, not fixed
- Integration tests (test_dlt_export_integration) not yet written (needs live server)

## Files Changed
- `tests/sprint_3/__init__.py` (new)
- `tests/sprint_3/conftest.py` (new)
- `tests/sprint_3/test_dlt_calculations.py` (new)
- `tests/sprint_3/test_dlt_export.py` (new)
- `tests/sprint_3/test_dlt_discrepancies.py` (new)
- `tests/sprint_3/test_dlt_excel_export.py` (new)
- `tests/regression/test_sprint_3_bugs.py` (new)
- `harness/contracts/sprint-3.md` (new)
- `harness/handoffs/sprint-3-handoff.md` (new)
