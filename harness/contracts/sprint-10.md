# Sprint 10 Contract: Full Combined Estimate — All 9 Workload Types

## Acceptance Criteria

- [ ] AC-1: A combined line item list with all 9 workload types passes through `build_estimate_excel()` without errors
- [ ] AC-2: Each workload type's DBU/hr calculation is correct when computed via `_calculate_dbu_per_hour()`
- [ ] AC-3: Each workload type's SKU is correctly determined via `_get_sku_type()`
- [ ] AC-4: Excel output has correct number of rows (11+ including Lakebase storage + Vector Search storage sub-rows)
- [ ] AC-5: Excel totals row uses SUM formulas spanning all data rows
- [ ] AC-6: Grand total (list and discounted) equals sum of individual row costs
- [ ] AC-7: Multi-row items (Lakebase, Vector Search) have separate storage rows with SKU=DATABRICKS_STORAGE
- [ ] AC-8: No broken formulas, no NaN, no $0 for non-zero configurations
- [ ] AC-9: Every computed formula cell matches expected formula pattern (=P{r}*L{r}, =N{r}*O{r}, etc.)
- [ ] AC-10: Notes column populated for relevant items
- [ ] AC-11: Token-based items (FMAPI) use token formula (=N*O) not hourly formula
- [ ] AC-12: Hourly items use hourly formula (=P*L)
- [ ] AC-13: Serverless items show no VM costs; Classic items show VM costs
- [ ] AC-14: Cross-workload consistency — same cloud/region/tier pricing applied uniformly

## Test Plan

### Unit tests: `tests/sprint_10/test_combined_calc.py`
- All 9 workload types' DBU/hr calculations in one test suite
- SKU mapping verification for each type
- Hours calculation for run-based vs hourly items

### Excel tests: `tests/sprint_10/test_combined_excel.py`
- Generate single Excel with all 9 workload types
- Verify row count (9 data rows + 2 storage sub-rows = 11)
- Verify formula patterns in each row match workload type
- Verify totals row SUM formulas span correct range

### Grand total tests: `tests/sprint_10/test_combined_totals.py`
- Totals row correctness
- Cross-workload total consistency
- Multi-row workload total inclusion (storage rows in SUM range)

### Regression tests: None needed (no prior evaluation bugs for Sprint 10)

## Line Items for Combined Estimate

1. **Jobs Serverless** — performance mode, 200 hrs/month
2. **All-Purpose Classic Photon** — 2 workers, 730 hrs/month
3. **DLT Pro Serverless** — standard mode, 100 hrs/month
4. **DBSQL Serverless Medium** — 1 cluster, 500 hrs/month
5. **Model Serving Medium GPU** — 200 hrs/month
6. **FMAPI Databricks** — llama-3-3-70b, input tokens, 100M/month
7. **FMAPI Proprietary** — anthropic claude-haiku-4-5, output tokens, 50M/month
8. **Vector Search Standard** — 5M vectors, 730 hrs/month
9. **Lakebase** — 4 CU, 2 HA nodes, 100GB storage, 730 hrs/month
