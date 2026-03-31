# Sprint 4 Handoff: DBSQL (Classic, Pro, Serverless — All Sizes)

## What Was Built

144 new tests covering DBSQL workload calculations, export pipeline, Excel formula verification, and frontend/backend alignment.

### Test Files Created
- `tests/sprint_4/conftest.py` — `make_line_item()` factory with DBSQL defaults
- `tests/sprint_4/dbsql_calc_helpers.py` — Frontend + backend calculation replicas
- `tests/sprint_4/test_dbsql_calculations.py` — 9 warehouse sizes, cluster multiplier, hours, SKU, pricing
- `tests/sprint_4/test_dbsql_export.py` — Backend `_calc_dbsql_dbu`, `_get_sku_type`, `_is_serverless_workload`
- `tests/sprint_4/test_dbsql_excel_export.py` — Excel formula cells, mode column, multi-type SKU presence
- `tests/sprint_4/test_dbsql_export_integration.py` — Single Serverless endpoint integration
- `tests/sprint_4/test_dbsql_integration_multi.py` — Classic + Pro + Serverless multi-type endpoint integration
- `tests/sprint_4/test_dbsql_discrepancies.py` — FE vs BE alignment (size, SKU, DBUs, pricing, cost)
- `tests/sprint_4/test_dbsql_vm_and_notes.py` — VM costs, display name, config details, edge cases

## How to Test
- Run: `python3 -m pytest tests/sprint_4/ -v`
- Live app: https://lakemeter-e2e-v2-335310294452632.aws.databricksapps.com
- Navigate to Calculator → add DBSQL line items with Classic/Pro/Serverless types

## Test Results
- `pytest` exit code: 0
- Tests: 563 total (144 new + 419 existing), 0 failures
- All files under 200 lines (max: 198 lines)

## Key Findings
- All 9 warehouse sizes correctly map to DBU/hr (2X-Small=4 through 4X-Large=528)
- Cluster multiplier works: DBU/hr = size_dbu × num_clusters
- SKU mapping correct: Classic→SQL_COMPUTE, Pro→SQL_PRO_COMPUTE, Serverless→SERVERLESS_SQL_COMPUTE
- Frontend and backend agree on all calculations (no discrepancies found)
- Fallback $/DBU: Classic=$0.22, Pro=$0.55, Serverless=$0.70
- Edge case: empty string warehouse size defaults to Small via falsy `or` (no warning)
- Edge case: 0 clusters → treated as 1 via falsy `or`
- Edge case: negative clusters → produces negative DBU (no guard in backend)

## Known Limitations
- Backend does not validate negative cluster counts (produces negative DBU)
- Empty string warehouse size silently defaults to Small (no warning)
- VM pricing for Classic/Pro DBSQL uses default estimates ($0.20/$0.10), not real instance prices

## Files Changed
- `tests/sprint_4/` — 10 new files (1228 lines total)
- `harness/contracts/sprint-4.md` — new
- `harness/handoffs/sprint-4-handoff.md` — new
