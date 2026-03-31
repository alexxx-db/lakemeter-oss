# Sprint 9 Handoff: Lakebase (CU Sizes, HA Nodes, Storage)

## What Was Built

111 tests covering all Lakebase calculation paths:

### Test Files
| File | Tests | Coverage |
|------|-------|----------|
| `test_lb_dbu_calc.py` | 44 | DBU/hr = CU × nodes, all CU sizes (0.5-112), multi-node, all clouds |
| `test_lb_sku_pricing.py` | 14 | SKU determination, pricing lookups, serverless classification |
| `test_lb_config_display.py` | 7 | Config display strings, partial fields |
| `test_lb_edge_cases.py` | 18 | Zero CU, None defaults, storage cost, max config, discounts |
| `test_lb_excel_compute.py` | 14 | Compute row formulas, SKU, serverless markers, 2-row output |
| `test_lb_excel_storage.py` | 14 | Storage sub-row: SKU, cost, rate, config, notes |

### Acceptance Criteria Status
- [x] AC-1: DBU/hr = CU × HA_nodes — 44 parametrized cases
- [x] AC-2: Storage cost = GB × $0.023/GB/month — 6 cases incl. max 8192 GB
- [x] AC-3: Monthly DBUs = DBU/hr × hours — 5 cases
- [x] AC-4: SKU = DATABASE_SERVERLESS_COMPUTE — verified across all configs & clouds
- [x] AC-5: SKU = DATABRICKS_STORAGE for storage row — verified in Excel
- [x] AC-6: Two rows per Lakebase item in Excel — compute + storage
- [x] AC-7: Storage row has direct cost, no DBU formula — DBUs/Mo = 0
- [x] AC-8: Always serverless, no VM costs — verified
- [x] AC-9: Config display shows "CU: X | Nodes: Y" — 7 cases
- [x] AC-10: Edge cases (zero CU warns, None defaults, max config) — 18 cases

## How to Test

```bash
cd lakemeter_app
python -m pytest tests/sprint_9/ -v
```

## Test Results

- `pytest` exit code: 0
- Sprint 9 tests: 111 passed
- Full suite: 1153 passed (no regressions)

## Key Findings

1. **DBU/hr formula confirmed**: `CU × HA_nodes` (NOT `× 2`)
2. **Storage rate**: $0.023/GB/month from `dbu-rates.json` (aws:us-east-1:PREMIUM). Fallback dict does NOT include DATABRICKS_STORAGE.
3. **Storage sub-row**: Always emitted (even for 0 GB). Uses direct cost in col 20, not DBU formula.
4. **Spec discrepancy resolved**: Storage uses `gb × $0.023` (from pricing JSON), not `$0.025` (that's the fallback for unfound regions which doesn't exist for this SKU).

## Files Changed

```
tests/sprint_9/__init__.py          (new)
tests/sprint_9/conftest.py          (new)
tests/sprint_9/lb_calc_helpers.py   (new)
tests/sprint_9/excel_helpers.py     (new)
tests/sprint_9/test_lb_dbu_calc.py  (new)
tests/sprint_9/test_lb_sku_pricing.py (new)
tests/sprint_9/test_lb_config_display.py (new)
tests/sprint_9/test_lb_edge_cases.py (new)
tests/sprint_9/test_lb_excel_compute.py (new)
tests/sprint_9/test_lb_excel_storage.py (new)
harness/contracts/sprint-9.md       (new)
harness/handoffs/sprint-9-handoff.md (new)
```
