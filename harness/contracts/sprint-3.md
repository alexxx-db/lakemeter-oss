# Sprint 3 Contract: DLT (Classic + Serverless, All Editions)

## Acceptance Criteria

### Calculation Tests
- [ ] AC-1: DLT Core Classic Standard: DBU/hr = (driver_dbu + worker_dbu x N) x 1.0
- [ ] AC-2: DLT Pro Classic Standard: Same formula, different $/DBU rate ($0.25)
- [ ] AC-3: DLT Advanced Classic Standard: Same formula, different $/DBU rate ($0.36)
- [ ] AC-4: DLT Core Classic Photon: DBU/hr = (driver_dbu + worker_dbu x N) x 2.0
- [ ] AC-5: DLT Pro Classic Photon: 2x multiplier applied
- [ ] AC-6: DLT Advanced Classic Photon: 2x multiplier applied
- [ ] AC-7: DLT Serverless Standard: base_dbu x 2 (photon built-in) x 1 (standard)
- [ ] AC-8: DLT Serverless Performance: base_dbu x 2 (photon built-in) x 2 (performance)
- [ ] AC-9: Hours calculation: run-based and direct hours both work for DLT
- [ ] AC-10: Monthly DBUs = DBU/hr x hours
- [ ] AC-11: DBU cost = monthly_dbus x $/DBU

### SKU Tests (Frontend)
- [ ] AC-12: DLT Classic Core -> DLT_CORE_COMPUTE
- [ ] AC-13: DLT Classic Pro -> DLT_PRO_COMPUTE
- [ ] AC-14: DLT Classic Advanced -> DLT_ADVANCED_COMPUTE
- [ ] AC-15: DLT Classic Core Photon -> DLT_CORE_COMPUTE_(PHOTON)
- [ ] AC-16: DLT Classic Advanced Photon -> DLT_ADVANCED_COMPUTE_(PHOTON)
- [ ] AC-17: DLT Serverless -> JOBS_SERVERLESS_COMPUTE (frontend)

### SKU Tests (Backend) — KNOWN DISCREPANCIES
- [ ] AC-18: Backend DLT Serverless -> DELTA_LIVE_TABLES_SERVERLESS (differs from FE)
- [ ] AC-19: Backend DLT Classic Photon -> DLT_{EDITION}_COMPUTE (missing _(PHOTON) suffix)

### Frontend/Backend Discrepancy Detection
- [ ] AC-20: DLT Serverless SKU: FE=JOBS_SERVERLESS_COMPUTE vs BE=DELTA_LIVE_TABLES_SERVERLESS
- [ ] AC-21: DLT Serverless $/DBU: FE=$0.39 (JOBS_SERVERLESS) vs BE=$0.50 (DELTA_LIVE_TABLES)
- [ ] AC-22: DLT Classic Photon SKU: FE=DLT_{ED}_COMPUTE_(PHOTON) vs BE=DLT_{ED}_COMPUTE (no _(PHOTON))

### VM Cost Tests
- [ ] AC-23: DLT Classic includes VM costs (driver + worker x N)
- [ ] AC-24: DLT Serverless has zero VM costs

### Export Tests
- [ ] AC-25: Excel export uses correct SKU for DLT variants
- [ ] AC-26: Excel formulas present (not static values) in computed columns
- [ ] AC-27: Excel SUM totals row correct
- [ ] AC-28: DLT edition appears in Config column

### Edge Cases
- [ ] AC-29: Zero hours = zero cost
- [ ] AC-30: No NaN or $0 for valid configurations

## Test Plan

- **Unit tests**: Frontend and backend calculation functions replicated in Python
- **Parametrized tests**: All 3 editions x (classic/classic-photon/serverless-std/serverless-perf)
- **Discrepancy tests**: Document FE vs BE differences (SKU, pricing)
- **Export tests**: Backend _get_sku_type and _calculate_dbu_per_hour for DLT
- **Regression tests**: Guard Sprint 1/2 bugs that also apply to DLT

## Production Readiness Items This Sprint
- N/A (testing-only run)
