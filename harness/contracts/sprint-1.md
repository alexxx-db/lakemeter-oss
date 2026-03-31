# Sprint 1 Contract: Jobs (Classic + Serverless) Calculation & Excel Verification

## Acceptance Criteria

### Frontend Calculation Logic (costCalculation.ts)
- [ ] Jobs Classic Standard: DBU/hr = (driver_dbu + worker_dbu × num_workers) × 1.0 (no photon)
- [ ] Jobs Classic Photon: DBU/hr = (driver_dbu + worker_dbu × num_workers) × 2.0 (photon multiplier)
- [ ] Jobs Serverless Standard: DBU/hr = (driver_dbu + worker_dbu × num_workers) × photon_mult × 1 (standard)
- [ ] Jobs Serverless Performance: DBU/hr = (driver_dbu + worker_dbu × num_workers) × photon_mult × 2 (performance)
- [ ] Hours calculation (run-based): hours = (runs_per_day × avg_runtime_minutes / 60) × days_per_month
- [ ] Hours calculation (direct): hours = hours_per_month
- [ ] Monthly DBUs = DBU/hr × hours_per_month
- [ ] SKU mapping: Classic→JOBS_COMPUTE, Photon→JOBS_COMPUTE_(PHOTON), Serverless→JOBS_SERVERLESS_COMPUTE
- [ ] No VM costs for serverless; VM costs present for classic

### Backend Export Logic (export.py)
- [ ] _get_sku_type returns correct SKU for each Jobs variant
- [ ] _calculate_dbu_per_hour returns correct DBU/hr for each Jobs variant
- [ ] _calculate_hours_per_month handles run-based vs direct hours correctly
- [ ] Excel formulas: DBUs/Mo = DBU/Hr × Hours/Mo (col 16 = col 15 × col 11)
- [ ] Excel formulas: DBU Cost (List) = DBUs/Mo × DBU Rate (col 20 = col 16 × col 17)
- [ ] Excel formulas: Discounted rate = List × (1 - discount%) (col 19 = col 17 × (1-col 18))
- [ ] Excel formulas: Total Cost = DBU Cost + VM Cost (col 27 = col 20 + col 26)
- [ ] Totals row uses SUM formulas

### Discrepancy Detection
- [ ] Compare frontend vs backend DBU/hr calculations for same inputs
- [ ] Compare frontend vs backend SKU assignments
- [ ] Document any differences found

## Test Plan
- Unit tests for frontend calculation logic (replicated in Python)
- Unit tests for backend export helper functions
- Integration tests: create mock line items, run through export pipeline
- Discrepancy tests: same inputs → compare frontend vs backend outputs

## Production Readiness Items This Sprint
- N/A (testing-only run)
