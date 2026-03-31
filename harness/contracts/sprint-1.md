# Sprint 1 Contract: Jobs (Classic + Serverless) Calculation & Excel Verification

## Iteration 2 — Addressing Evaluator Feedback from Iteration 5 Eval (7.90/10)

### Required Improvements (from eval)
1. **BUG-S1-12**: num_workers default discrepancy — backend was `or 1`, now `or 0` (FIXED in code)
2. **BUG-S1-13**: Hours fallback discrepancy — backend was 11 hrs, now 0 (FIXED in code)
3. **BUG-S1-14**: Handoff test count inconsistency — update handoff with accurate counts

### Acceptance Criteria

#### Frontend Calculation Logic (costCalculation.ts)
- [x] Jobs Classic Standard: DBU/hr = (driver_dbu + worker_dbu × num_workers) × 1.0 (no photon)
- [x] Jobs Classic Photon: DBU/hr = (driver_dbu + worker_dbu × num_workers) × 2.0 (photon multiplier)
- [x] Jobs Serverless Standard: DBU/hr = (driver_dbu + worker_dbu × num_workers) × photon_mult × 1 (standard)
- [x] Jobs Serverless Performance: DBU/hr = (driver_dbu + worker_dbu × num_workers) × photon_mult × 2 (performance)
- [x] Hours calculation (run-based): hours = (runs_per_day × avg_runtime_minutes / 60) × days_per_month
- [x] Hours calculation (direct): hours = hours_per_month
- [x] Monthly DBUs = DBU/hr × hours_per_month
- [x] SKU mapping: Classic→JOBS_COMPUTE, Photon→JOBS_COMPUTE_(PHOTON), Serverless→JOBS_SERVERLESS_COMPUTE
- [x] No VM costs for serverless; VM costs present for classic

#### Backend Export Logic
- [x] _get_sku_type returns correct SKU for each Jobs variant
- [x] _calculate_dbu_per_hour returns correct DBU/hr for each Jobs variant
- [x] _calculate_hours_per_month handles run-based vs direct hours correctly
- [x] num_workers defaults to 0 (not 1) when unset — BUG-S1-12 FIXED
- [x] Hours fallback returns 0 (not 11) when no data — BUG-S1-13 FIXED
- [x] Excel formulas: DBUs/Mo = DBU/Hr × Hours/Mo (col 16 = col 15 × col 11)
- [x] Excel formulas: DBU Cost (List) = DBUs/Mo × DBU Rate (col 20 = col 16 × col 17)
- [x] Excel formulas: Discounted rate = List × (1 - discount%) (col 19 = col 17 × (1-col 18))
- [x] Excel formulas: Total Cost = DBU Cost + VM Cost (col 27 = col 20 + col 26)
- [x] Totals row uses SUM formulas

#### Discrepancy Detection
- [x] Frontend vs backend DBU/hr calculations match for all 4 Jobs configs
- [x] Frontend vs backend SKU assignments match
- [x] Frontend vs backend hours calculation aligned (both return 0 when no data)
- [x] Frontend vs backend num_workers default aligned (both use 0)

#### NaN / $0 Regression
- [x] All 4 Jobs configurations produce non-zero, non-NaN costs
- [x] Zero workers produces driver-only DBU (not NaN)
- [x] Zero hours produces zero cost (not 11 hrs fallback)

### Test Plan
- Unit tests for frontend calculation logic (replicated in Python)
- Unit tests for backend export helper functions (_get_sku_type, _calculate_dbu_per_hour, etc.)
- Integration tests: mock line items → export endpoint → openpyxl verification
- Discrepancy tests: same inputs → verify frontend == backend
- Regression tests for BUG-S1-5, S1-6, S1-12, S1-13
- NaN/$0 parametric edge case tests across all 4 configs

### Production Readiness Items This Sprint
- N/A (testing-only run)
