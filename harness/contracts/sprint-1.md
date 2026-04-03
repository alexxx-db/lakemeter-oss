# Sprint 1 Contract: JOBS + ALL_PURPOSE Parity (Classic/Photon/Serverless)

## Acceptance Criteria

- [ ] Driver DBU fallback rate in backend matches frontend (0.5, not 0.25)
- [ ] JOBS Classic: DBU/hr, $/DBU, hours/mo, monthly DBUs, monthly cost match UI within $0.01
- [ ] JOBS Classic Photon: Same parity with photon multiplier applied
- [ ] JOBS Serverless Standard: Same parity with photon always-on + 1x mode multiplier
- [ ] JOBS Serverless Performance: Same parity with photon always-on + 2x mode multiplier
- [ ] ALL_PURPOSE Classic: DBU/hr, $/DBU, hours/mo, monthly DBUs, monthly cost match UI
- [ ] ALL_PURPOSE Classic Photon: Same parity with photon multiplier applied
- [ ] ALL_PURPOSE Serverless: Same parity with always-performance (2x) + photon always-on
- [ ] SKU product type correct for all JOBS/ALL_PURPOSE variants
- [ ] End-to-end Excel generation produces correct values for JOBS/ALL_PURPOSE items
- [ ] Edge cases: zero workers, 8+ workers, run-based hours, direct hours, large worker counts
- [ ] All existing parity tests still pass (no regressions)

## Bugs Found (Code Review)

### BUG-1: Driver DBU fallback mismatch
- **Frontend** (`costCalculation.ts:250`): `driverDBURate = 0.5`
- **Backend** (`calculations.py:56`): `driver_dbu = 0.25`
- **Impact**: When instance type is not found in pricing JSON, backend computes lower DBU/hr
- **Fix**: Change backend fallback to 0.5 to match frontend

## Test Plan

### Unit tests (parity)
- JOBS Classic: 2, 4, 8 workers with known instance types
- JOBS Classic: zero workers (driver only)
- JOBS Classic: run-based hours vs direct hours
- JOBS Photon: verified photon multiplier from JSON
- JOBS Serverless Standard: 1x mode multiplier
- JOBS Serverless Performance: 2x mode multiplier
- ALL_PURPOSE Classic: basic, photon, zero workers
- ALL_PURPOSE Serverless: always performance (2x)
- Fallback rates: items with unknown instance types should use 0.5 fallback for both driver and worker

### Integration tests (Excel generation)
- Generate Excel for a JOBS Classic item → verify DBU/hr, cost cells
- Generate Excel for JOBS Serverless Performance → verify cells
- Generate Excel for ALL_PURPOSE Serverless → verify cells
- Verify Excel formulas (DBUs/Mo = DBU/Hr × Hours/Mo) produce correct cached values

### Regression tests
- All 9 existing parity tests must continue to pass
- All sprint_10 tests must continue to pass

## Files to Modify
- `backend/app/routes/export/calculations.py` — fix driver DBU fallback
- `tests/parity/test_parity_jobs.py` — add edge case tests
- `tests/parity/test_parity_allpurpose.py` — add edge case tests
- New: `tests/parity/test_excel_jobs_allpurpose.py` — end-to-end Excel generation tests
