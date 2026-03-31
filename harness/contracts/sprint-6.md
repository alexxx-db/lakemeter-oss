# Sprint 6 Contract: FMAPI Databricks (Token + Provisioned)

## Feature
Exhaustive testing of FMAPI_DATABRICKS workload type — token-based (input/output) and provisioned (scaling/entry) rate types across all models and clouds.

## Acceptance Criteria

### Rate Lookups (AC-1 to AC-8)
- [ ] AC-1: Token-based input rates match pricing JSON for all AWS models
- [ ] AC-2: Token-based output rates match pricing JSON (output > input for same model)
- [ ] AC-3: Provisioned scaling rates match pricing JSON for all AWS models
- [ ] AC-4: Provisioned entry rates match pricing JSON for all AWS models
- [ ] AC-5: Azure rates match pricing JSON (same models available)
- [ ] AC-6: GCP rates match pricing JSON
- [ ] AC-7: Cross-cloud rate consistency (same model = same rate across clouds)
- [ ] AC-8: All JSON entries have required fields (dbu_rate, input_divisor, is_hourly, sku_product_type)

### SKU & Pricing (AC-9 to AC-12)
- [ ] AC-9: SKU = SERVERLESS_REAL_TIME_INFERENCE for all FMAPI_DATABRICKS items
- [ ] AC-10: Fallback $/DBU = $0.07 for SERVERLESS_REAL_TIME_INFERENCE
- [ ] AC-11: FMAPI_DATABRICKS is always serverless (no VM costs)
- [ ] AC-12: _calculate_dbu_per_hour returns 0 for FMAPI (token-based, not hourly)

### Backend Export Calculations (AC-13 to AC-18)
- [ ] AC-13: Token-based: monthly_dbus = quantity_M × dbu_per_1M_tokens
- [ ] AC-14: Provisioned: monthly_dbus = hours × dbu_per_hour
- [ ] AC-15: Token-based items have hours=0 in export
- [ ] AC-16: Provisioned items use fmapi_quantity as hours
- [ ] AC-17: _is_fmapi_hourly returns True for provisioned, False for token
- [ ] AC-18: _get_fmapi_dbu_per_million returns (rate, True) for known models, (0, False) for unknown

### Config Display (AC-19 to AC-22)
- [ ] AC-19: Display name = "Foundation Models (Databricks)"
- [ ] AC-20: Config details show "Model: {model} | Rate: {type} | Tokens: {qty}M/mo" for tokens
- [ ] AC-21: Config details show "Model: {model} | Rate: Provisioned Scaling | Hours: {qty}" for provisioned
- [ ] AC-22: Rate type display names correct (Input Tokens, Output Tokens, Provisioned Scaling, Provisioned Entry)

### Excel Export (AC-23 to AC-28)
- [ ] AC-23: Token-based items use token formula (=N*O) for DBUs/Mo, not hourly formula
- [ ] AC-24: Provisioned items use hours-based formula (=P*L) for DBUs/Mo
- [ ] AC-25: Token columns (12-14) populated for token items, "-" for provisioned
- [ ] AC-26: Excel has formulas (not static values) in computed columns
- [ ] AC-27: Excel SUM totals row correct across all items
- [ ] AC-28: Excel SKU = SERVERLESS_REAL_TIME_INFERENCE

### Edge Cases (AC-29 to AC-34)
- [ ] AC-29: Unknown model returns (0, False) with warning
- [ ] AC-30: Zero quantity = zero DBUs/cost
- [ ] AC-31: No NaN for any valid model+rate_type combination
- [ ] AC-32: Output rate > input rate for models with both
- [ ] AC-33: provisioned_entry rate <= provisioned_scaling rate (or equal)
- [ ] AC-34: Case-insensitive fallback lookup works

## Test Plan
- Unit tests: Rate lookups, calculation functions, display helpers
- Integration tests: Real .xlsx generation and validation
- Edge cases: NaN guards, unknown models, zero quantities
- Cross-cloud: Verify rate consistency

## Files to Create
- tests/sprint_6/__init__.py
- tests/sprint_6/conftest.py
- tests/sprint_6/fmapi_db_calc_helpers.py
- tests/sprint_6/test_fmapi_db_rates.py
- tests/sprint_6/test_fmapi_db_sku_pricing.py
- tests/sprint_6/test_fmapi_db_export_calc.py
- tests/sprint_6/test_fmapi_db_config_display.py
- tests/sprint_6/test_fmapi_db_excel_export.py
- tests/sprint_6/test_fmapi_db_edge_cases.py
