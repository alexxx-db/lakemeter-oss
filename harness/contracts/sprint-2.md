# Sprint 2 Contract: All-Purpose (Classic + Serverless)

## Acceptance Criteria

### Calculation Tests
- [ ] AC-1: All-Purpose Classic Standard: DBU/hr = (driver_dbu + worker_dbu x N) x 1.0
- [ ] AC-2: All-Purpose Classic Photon: DBU/hr = (driver_dbu + worker_dbu x N) x 2.0
- [ ] AC-3: All-Purpose Serverless: frontend always forces performance mode (2x serverless multiplier)
- [ ] AC-4: All-Purpose Serverless: photon always on (built-in 2x) -> total = base x 2 x 2 = 4x
- [ ] AC-5: Run-based hours: (runs/day x mins/60) x days/month
- [ ] AC-6: Direct hours: hours_per_month passthrough
- [ ] AC-7: Monthly DBUs = DBU/hr x hours
- [ ] AC-8: DBU cost = monthly_dbus x $/DBU

### SKU Tests
- [ ] AC-9: Classic Standard -> ALL_PURPOSE_COMPUTE
- [ ] AC-10: Classic Photon -> ALL_PURPOSE_COMPUTE_(PHOTON)
- [ ] AC-11: Serverless -> ALL_PURPOSE_SERVERLESS_COMPUTE

### VM Cost Tests
- [ ] AC-12: Classic includes VM costs (driver + worker x N)
- [ ] AC-13: Serverless has zero VM costs

### Frontend/Backend Discrepancy Detection
- [ ] AC-14: Detect ALL_PURPOSE Serverless multiplier discrepancy (FE always 2x, BE uses stored mode)
- [ ] AC-15: Detect num_workers=0 default discrepancy (FE=0, BE=1)
- [ ] AC-16: Detect hours fallback discrepancy (FE=0, BE=11)

### Export Tests
- [ ] AC-17: Excel export uses correct SKU for All-Purpose variants
- [ ] AC-18: Excel formulas present (not static values) in computed columns
- [ ] AC-19: Excel SUM totals row correct

### Edge Cases
- [ ] AC-20: Zero hours = zero cost
- [ ] AC-21: Large cluster (many workers)
- [ ] AC-22: Fractional DBU rates
- [ ] AC-23: No NaN or $0 for valid configurations

## Test Plan

- **Unit tests**: Frontend and backend calculation functions replicated in Python
- **Parametrized tests**: Multiple instance types and cluster configurations
- **Discrepancy tests**: Compare frontend vs backend output for each config
- **Export tests**: TestClient-based Excel export verification via openpyxl
- **Regression tests**: Guard Sprint 1 bugs that also apply to All-Purpose

## Production Readiness Items This Sprint
- N/A (testing-only run)
