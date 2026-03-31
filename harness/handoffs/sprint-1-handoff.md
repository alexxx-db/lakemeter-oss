# Sprint 1 Handoff: Jobs (Classic + Serverless) Calculation & Excel Verification

## What Was Built

### Test Files
- `tests/conftest.py` — Shared fixtures loading pricing JSON data
- `tests/sprint_1/test_jobs_calculations.py` — 30 tests: Frontend calculation logic replicated in Python, covering all 4 Jobs variants
- `tests/sprint_1/test_jobs_export.py` — 27 tests: Backend export helper functions tested directly
- `tests/sprint_1/test_jobs_discrepancies.py` — 8 tests: Documented frontend vs backend discrepancies

### Test Coverage
- **Hours calculation**: Run-based (runs × minutes × days), direct hours, priority rules, fallbacks
- **DBU/hr calculation**: All 4 configurations (Classic Standard, Classic Photon, Serverless Standard, Serverless Performance)
- **SKU mapping**: Verified correct product type assignment for all variants
- **DBU pricing**: Verified $/DBU lookup from pricing JSON (aws:us-east-1:PREMIUM)
- **End-to-end**: Full calculation chain (hours → DBU/hr → monthly DBUs → cost)
- **Edge cases**: Zero workers, large clusters, fractional rates, no-usage fallback

## How to Test

```bash
cd "/Users/steven.tan/Desktop/Ent 1 - Q4 FY 2026 Team Project/lakemeter_app"
python3 -m pytest tests/sprint_1/ -v
```

## Test Results

```
65 passed, 11 warnings in 1.25s
```

- All 65 tests PASSED
- Warnings are Pydantic deprecation notices (pre-existing, not related to tests)

## Key Findings: Frontend vs Backend Discrepancies

### DISCREPANCY #1: Serverless Photon Handling (CRITICAL)
- **Frontend** (costCalculation.ts:273-276): Photon is ALWAYS enabled for serverless (built-in), multiplier = 2.0
- **Backend** (export.py:330-331): Photon only applied if `photon_enabled=True` flag is set
- **Impact**: For serverless Jobs with `photon_enabled=False`, frontend shows **2x higher** DBU/hr than Excel export
- **Example**: Base 3.0 DBU/hr → Frontend: 6.0, Backend: 3.0

### DISCREPANCY #2: Default num_workers (MEDIUM)
- **Frontend** (costCalculation.ts:125): `num_workers || 0` → defaults to 0
- **Backend** (export.py:327): `int(num_workers or 1)` → defaults to 1
- **Impact**: When `num_workers=0`, frontend shows driver-only cost, backend adds 1 worker
- **Example**: Frontend: 1.0 DBU/hr, Backend: 2.0 DBU/hr

### DISCREPANCY #3: Hours Fallback (LOW)
- **Frontend**: Returns 0 hours if no usage config
- **Backend**: Returns 11 hours fallback `(1 run × 30 min / 60) × 22 days`
- **Impact**: Rare — only when a line item has no usage configuration at all

## Known Limitations
- Tests verify calculation logic only (not live browser testing — that's for Visual QA)
- VM cost lookup not tested (requires live VM pricing data or mock)
- Excel formula cell validation not tested (would need openpyxl to read generated .xlsx)

## Files Changed
- `tests/__init__.py` (new)
- `tests/conftest.py` (new)
- `tests/sprint_1/__init__.py` (new)
- `tests/sprint_1/test_jobs_calculations.py` (new)
- `tests/sprint_1/test_jobs_export.py` (new)
- `tests/sprint_1/test_jobs_discrepancies.py` (new)
- `harness/contracts/sprint-1.md` (new)
- `harness/handoffs/sprint-1-handoff.md` (new)
