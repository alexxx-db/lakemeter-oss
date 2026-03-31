# Sprint 4 Contract: DBSQL (Classic, Pro, Serverless — All Sizes)

## Acceptance Criteria
- [ ] All 9 warehouse sizes map to correct DBU/hr rates (2X-Small=4 through 4X-Large=528)
- [ ] Cluster multiplier works: DBU/hr = size_dbu × num_clusters
- [ ] SKU mapping: Classic→SQL_COMPUTE, Pro→SQL_PRO_COMPUTE, Serverless→SERVERLESS_SQL_COMPUTE
- [ ] Serverless detection: DBSQL with warehouse_type=SERVERLESS returns is_serverless=True
- [ ] VM costs: Classic/Pro have VM costs; Serverless has zero VM costs
- [ ] Frontend and backend calculations agree on DBU/hr for all configurations
- [ ] Excel formulas: DBUs/Mo = DBU/Hr × Hours/Mo (formula, not static)
- [ ] Excel formulas: DBU Cost = DBUs/Mo × DBU Rate (formula, not static)
- [ ] Excel totals row has SUM formulas across all data rows
- [ ] No NaN, #REF!, or $0 for non-zero configurations
- [ ] Unknown warehouse size falls back to Small (12 DBU) with warning
- [ ] Fallback $/DBU prices: Classic=$0.22, Pro=$0.55, Serverless=$0.70

## Test Plan
- Unit tests: warehouse size mapping, SKU type, serverless detection, cluster multiplier
- Export tests: _calc_dbsql_dbu, _get_sku_type, _is_serverless_workload
- Excel tests: formula verification, row structure, storage handling
- Integration tests: full endpoint with mocked DB, verify Excel output
- Discrepancy tests: frontend vs backend alignment
- Edge case tests: unknown size, zero clusters, missing fields

## Files to Create
- tests/sprint_4/conftest.py
- tests/sprint_4/dbsql_calc_helpers.py
- tests/sprint_4/test_dbsql_calculations.py
- tests/sprint_4/test_dbsql_export.py
- tests/sprint_4/test_dbsql_excel_export.py
- tests/sprint_4/test_dbsql_export_integration.py
- tests/sprint_4/test_dbsql_discrepancies.py
- tests/sprint_4/test_dbsql_vm_and_notes.py
