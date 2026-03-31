# Sprint 9 Contract: Lakebase (CU Sizes, HA Nodes, Storage)

## Acceptance Criteria

- [AC-1] DBU/hr = CU × HA_nodes for all valid CU sizes (0.5, 1-32, 36-112)
- [AC-2] Storage cost = storage_gb × $0.023/GB/month (DATABRICKS_STORAGE rate)
- [AC-3] Monthly DBUs = DBU/hr × hours_per_month (730 for always-on)
- [AC-4] SKU = DATABASE_SERVERLESS_COMPUTE for compute row
- [AC-5] SKU = DATABRICKS_STORAGE for storage sub-row
- [AC-6] Excel export has TWO rows per Lakebase item (compute + storage)
- [AC-7] Storage sub-row has storage_cost_monthly = gb × rate, no DBU formula
- [AC-8] Lakebase is always serverless (no VM costs)
- [AC-9] Config display shows "CU: X | Nodes: Y"
- [AC-10] Edge cases: 0 CU warns, None defaults, max config (112 CU, 3 nodes, 8192 GB)

## Test Plan

### Unit Tests
- `test_lb_dbu_calc.py`: DBU/hr for all CU × node combos (parametrized)
- `test_lb_sku_pricing.py`: SKU determination, DBU rate lookup, storage rate
- `test_lb_config_display.py`: Config detail string generation
- `test_lb_edge_cases.py`: Zero CU, None fields, warnings, max values

### Excel Export Tests
- `test_lb_excel_compute.py`: Compute row formulas (DBUs/Mo, DBU cost, totals)
- `test_lb_excel_storage.py`: Storage sub-row (cost, SKU, notes, no DBU formula)

## API Contract

- No new endpoints — testing existing calculation + export logic
- Functions under test: `_calculate_dbu_per_hour`, `_get_sku_type`, `_get_dbu_price`, `write_storage_subrow`, `_lakebase_details`
