# Sprint 5 Contract: Model Serving (All GPU Types)

## Acceptance Criteria

### GPU Rate Tests (Frontend + Backend)
- [ ] AC-1: CPU → 1.0 DBU/hr (AWS)
- [ ] AC-2: GPU Small T4 → 10.48 DBU/hr (AWS)
- [ ] AC-3: GPU Medium A10G 1x → 20.0 DBU/hr (AWS)
- [ ] AC-4: GPU Medium A10G 4x → 112.0 DBU/hr (AWS)
- [ ] AC-5: GPU Medium A10G 8x → 290.8 DBU/hr (AWS)
- [ ] AC-6: GPU XLarge A100 40GB 8x → 538.4 DBU/hr (AWS)
- [ ] AC-7: GPU XLarge A100 80GB 8x → 628.0 DBU/hr (AWS)
- [ ] AC-8: Azure CPU → 1.0 DBU/hr
- [ ] AC-9: Azure GPU Small T4 → 10.48 DBU/hr
- [ ] AC-10: Azure XLarge A100 80GB 1x → 78.6 DBU/hr
- [ ] AC-11: GCP CPU → 1.0 DBU/hr
- [ ] AC-12: GCP GPU Medium G2 → 5.0 DBU/hr

### SKU Tests
- [ ] AC-13: SKU = SERVERLESS_REAL_TIME_INFERENCE for all GPU types
- [ ] AC-14: $/DBU = $0.07 (fallback for SERVERLESS_REAL_TIME_INFERENCE)

### Serverless Detection
- [ ] AC-15: Model Serving always detected as serverless (no VM costs)
- [ ] AC-16: VM cost columns = 0 for all Model Serving items

### Hours Calculation
- [ ] AC-17: Direct hours: hours_per_month used as-is
- [ ] AC-18: Run-based: (runs_per_day × avg_runtime_minutes / 60) × days_per_month
- [ ] AC-19: Run-based priority: run-based overrides hours_per_month when both set

### Monthly Cost Calculation
- [ ] AC-20: Monthly DBUs = DBU/hr × hours_per_month
- [ ] AC-21: DBU Cost = monthly_dbus × $/DBU
- [ ] AC-22: Total Cost = DBU Cost (no VM costs)

### Config Display
- [ ] AC-23: GPU name label mapping correct (CPU, Small T4, Medium A10G, etc.)
- [ ] AC-24: Config details show "GPU: {label}" format

### Excel Export
- [ ] AC-25: Excel row has correct SKU (SERVERLESS_REAL_TIME_INFERENCE)
- [ ] AC-26: Excel formulas present in computed columns (not static values)
- [ ] AC-27: Excel SUM totals row correct
- [ ] AC-28: Excel "Serverless" mode label for all Model Serving rows

### Edge Cases
- [ ] AC-29: Unknown GPU type defaults to 0 DBU/hr with warning
- [ ] AC-30: Zero hours = zero cost (no NaN)
- [ ] AC-31: Missing gpu_type defaults to 'cpu'
- [ ] AC-32: No NaN for any valid GPU + hours combination

## Test Plan

- **Unit tests**: Frontend and backend calc functions replicated in Python
- **Parametrized tests**: All 14 GPU types across 3 clouds
- **Export tests**: Backend `_get_sku_type`, `_calc_model_serving_dbu`, display helpers
- **Excel E2E tests**: Real .xlsx verification with formulas
- **Edge case tests**: NaN guards, unknown GPUs, zero hours

## Production Readiness Items This Sprint
- N/A (testing-only run)
