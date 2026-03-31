# Sprint 8 Contract: Vector Search (Standard + Storage Optimized)

## Acceptance Criteria

### DBU Calculation (AC-1 to AC-5)
- [ ] AC-1: Standard mode — units = capacity_M * 1,000,000 / 2,000,000; DBU/hr = units * 4.0
- [ ] AC-2: Storage Optimized — units = capacity_M * 1,000,000 / 64,000,000; DBU/hr = units * 18.29
- [ ] AC-3: Monthly DBUs = DBU/hr * hours_per_month (hourly formula, not token)
- [ ] AC-4: All 3 clouds (aws, azure, gcp) use same rates (4.0 / 18.29)
- [ ] AC-5: Zero capacity produces 0 DBU/hr with warning

### SKU & Pricing (AC-6 to AC-8)
- [ ] AC-6: SKU = VECTOR_SEARCH_ENDPOINT for all Vector Search items
- [ ] AC-7: $/DBU lookup uses VECTOR_SEARCH_ENDPOINT key (fallback $0.088)
- [ ] AC-8: Vector Search is always serverless (no VM costs)

### Excel Export (AC-9 to AC-14)
- [ ] AC-9: Main compute row has formula =P{r}*L{r} for DBUs/Mo (hourly formula)
- [ ] AC-10: Storage sub-row emitted for every Vector Search item
- [ ] AC-11: Storage sub-row SKU = DATABRICKS_STORAGE
- [ ] AC-12: Storage GB approximated as capacity_millions (1M vectors ~ 1 GB)
- [ ] AC-13: Storage cost = storage_gb * $/GB rate (DATABRICKS_STORAGE lookup)
- [ ] AC-14: Totals SUM formula spans both compute and storage rows

### Config Display (AC-15 to AC-16)
- [ ] AC-15: Config shows "Mode: Standard" or "Mode: Storage Optimized"
- [ ] AC-16: Config shows "Capacity: {N}M vectors" when set

### Edge Cases (AC-17 to AC-20)
- [ ] AC-17: Fractional capacity (e.g., 0.5M) calculates correctly
- [ ] AC-18: Large capacity (1000M) calculates correctly
- [ ] AC-19: Missing mode defaults to 'standard'
- [ ] AC-20: No NaN or negative values in any output

## Test Plan
- Unit tests: DBU/hr calculation for standard & storage_optimized across all clouds
- Unit tests: SKU mapping, pricing lookups
- Integration tests: Full Excel export with formula verification
- Edge case tests: Zero, fractional, large capacity; missing mode
- Parametrized tests: All 6 cloud:mode combinations × multiple capacities
