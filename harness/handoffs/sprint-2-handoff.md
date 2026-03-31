# Sprint 2 Handoff: All-Purpose (Classic + Serverless)

## What Was Built

99 new tests across 6 files covering All-Purpose workload type calculations:

| File | Tests | Coverage |
|------|-------|----------|
| `test_allpurpose_calculations.py` | 26 | Frontend/backend formula replication, hours, classic/photon/serverless, edge cases |
| `test_allpurpose_discrepancies.py` | 12 | FE/BE alignment tests, **new serverless mode discrepancy** |
| `test_allpurpose_export.py` | 15 | Backend export helpers: SKU, DBU/hr, hours, serverless detection, pricing |
| `test_allpurpose_excel_export.py` | 22 | Excel formula presence, computed values, totals row SUM formulas |
| `test_allpurpose_vm_and_notes.py` | 12 | VM cost presence/absence, display name, config details, pricing tiers |
| `test_allpurpose_export_integration.py` | 12 | FastAPI TestClient with mocked DB/auth, real export pipeline |

### Shared Test Infrastructure
- `tests/sprint_2/conftest.py` — `make_line_item(**kwargs)` factory with ALL_PURPOSE defaults
- Fixtures: `aws_instance_rates`, `us_east_1_premium_rates` (from conftest.py)

## Key Findings

### NEW Discrepancy: ALL_PURPOSE Serverless Mode (FE/BE Mismatch)
- **Frontend** (`costCalculation.ts` line 314): Hardcodes `serverlessMultiplier = 2` for ALL_PURPOSE regardless of `serverless_mode`
- **Backend** (`export.py` line 333): Uses `mode_multiplier = 2 if serverless_mode == 'performance' else 1` — no ALL_PURPOSE override
- **Impact**: When `serverless_mode='standard'`, FE shows 20.0 DBU/hr but Excel export shows 10.0 DBU/hr (2x ratio)
- **Documented in**: `test_allpurpose_discrepancies.py::TestServerlessModeDiscrepancy`

### Known Discrepancies (from Sprint 1, still present)
1. **num_workers default**: FE uses 0 when null, BE defaults to 1
2. **Hours fallback**: FE returns 0 when no input, BE returns 11 hours

## How to Test

```bash
# Run Sprint 2 tests only
cd "/Users/steven.tan/Desktop/Ent 1 - Q4 FY 2026 Team Project/lakemeter_app"
python -m pytest tests/sprint_2/ -v

# Run full suite (Sprint 1 + Sprint 2)
python -m pytest tests/ -v
```

## Test Results

```
238 passed, 0 failed, 0 errors
- Sprint 1: 139 tests
- Sprint 2: 99 tests
```

## Files Changed
- `tests/sprint_2/__init__.py` (new)
- `tests/sprint_2/conftest.py` (new)
- `tests/sprint_2/test_allpurpose_calculations.py` (new)
- `tests/sprint_2/test_allpurpose_discrepancies.py` (new)
- `tests/sprint_2/test_allpurpose_export.py` (new)
- `tests/sprint_2/test_allpurpose_excel_export.py` (new)
- `tests/sprint_2/test_allpurpose_vm_and_notes.py` (new)
- `tests/sprint_2/test_allpurpose_export_integration.py` (new)

## Known Limitations
- VM cost values in tests use hardcoded $0.20/$0.10 (matching backend export.py lines 897-903) — actual VM pricing is more complex
- The serverless mode discrepancy is documented but not fixed (requires product decision on which behavior is correct)
- No browser E2E tests — those are for Visual QA agent
