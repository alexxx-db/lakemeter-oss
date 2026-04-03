# Sprint 3 Handoff: Workload Guides — SQL, AI/ML, and Lakebase (Iteration 2)

## What Was Built (Iteration 1)

### 6 Workload Guides Rewritten

All 6 guides follow the Sprint 2 pattern: real-world scenario → worked example with actual numbers → configuration reference → formulas → tips → common mistakes → Excel export.

1. **DBSQL Warehouses** (`docs-site/docs/user-guide/dbsql-warehouses.md`)
   - Scenario: Pro Medium warehouse, 2 clusters, 176 hrs/month
   - Worked example: 48 DBU/hr × 176 = 8,448 DBUs × $0.55 = $4,646.40
   - Classic vs Pro vs Serverless comparison table
   - Warehouse size → DBU/hour reference table (2X-Small to 4X-Large)

2. **Model Serving** (`docs-site/docs/user-guide/model-serving.md`)
   - Scenario: A10G 1x GPU, 176 hrs/month
   - Worked example: 20.0 DBU/hr × 176 = 3,520 × $0.07 = $246.40
   - GPU comparison (CPU $12.32 vs T4 $129.11 vs A10G $246.40 for same hours)
   - 14 GPU types table with typical use cases

3. **Vector Search** (`docs-site/docs/user-guide/vector-search.md`)
   - Scenario: Standard endpoint, 10M vectors, 50 GB storage, 730 hrs
   - Worked example with CEILING function: CEILING(10M/2M) = 5 units × 4.0 = 20.0 DBU/hr
   - Free storage tier calculation: 5 units × 20 GB = 100 GB free
   - Standard vs Storage-Optimized comparison

4. **FMAPI Databricks** (`docs-site/docs/user-guide/fmapi-databricks.md`)
   - Scenario: Llama 3.3 70B, 50M input + 10M output tokens
   - Worked example: Input 50 × 7.143 × $0.07 = $25.00, Output 10 × 21.429 × $0.07 = $15.00
   - Provisioned throughput comparison ($17,520/mo for 730 hrs)

5. **FMAPI Proprietary** (`docs-site/docs/user-guide/fmapi-proprietary.md`)
   - Scenario: Claude Sonnet 4.5, 5M input + 1M output tokens, global/long context
   - Worked example: Input 5 × 85.714 × $0.07 = $30.00, Output 1 × 321.429 × $0.07 = $22.50
   - Endpoint type comparison (global $52.50 vs in-geo $57.75)

6. **Lakebase** (`docs-site/docs/user-guide/lakebase.md`)
   - Scenario: 4 CU, 2 nodes, 500 GB, 730 hrs
   - Worked example: Compute $2,336.00 + Storage $172.50 = $2,508.50

### Sidebar Restructured

Two categories: Compute Workloads (overview + Jobs, All-Purpose, DLT, DBSQL) and AI/ML & Data Services (Model Serving, Vector Search, FMAPI Databricks, FMAPI Proprietary, Lakebase).

### Workloads Overview Rewritten

Transformed into a decision guide with quick decision table, category breakdown, and pricing tier restrictions.

## What Was Fixed (Iteration 2)

### Lakebase Guide Accuracy Fixes
- **CU sizes corrected**: Changed from "0.5 to 112" to "1, 2, 4, or 8" matching the actual UI dropdown options
- **Removed half-CU (0.5) example**: The UI and backend (Integer column) don't support half-CU values
- **Removed backup retention field from config reference**: The field exists in the backend but is NOT shown in the Lakemeter UI — it's a hidden/managed field with default 7 days
- **Removed CU=0 edge case**: Not a valid UI option
- **Updated tips and common mistakes**: Replaced 0.5 CU references with accurate "1 CU is the smallest option" guidance

### FMAPI Proprietary Context Length Fixes
- **Default corrected**: Changed default context length from "All" to "Long" — the UI defaults to "long" when switching providers (WorkloadForm.tsx line 1710)
- **Context length descriptions reordered**: Listed Long first (as default), then Short, then All — matching actual usage priority
- **Added note**: "Not all models support all context lengths — Lakemeter automatically filters available options based on the selected model"

### Verification Summary
All pricing numbers re-verified against pricing bundle JSONs:
- DBSQL: Small=12, Medium=24 DBU/hr; Classic $0.22, Pro $0.55, Serverless $0.70 ✓
- Model Serving: CPU=1.0, T4=10.48, A10G 1x=20.0 DBU/hr; $0.07/DBU ✓
- Vector Search: Standard=4.0 DBU/hr (2M divisor), Storage-Opt=18.29 (64M divisor) ✓
- FMAPI DB: Llama 3.3 70B input=7.143, output=21.429, provisioned=342.857 ✓
- FMAPI Prop: Claude Sonnet 4.5 global/long input=85.714, output=321.429 ✓
- FMAPI Prop: Claude Sonnet 4.5 in-geo/long input=94.285, output=353.572 ✓
- Lakebase: DATABASE_SERVERLESS_COMPUTE=$0.40/DBU ✓

## How to Test

- Start: `cd docs-site && npm run start`
- Navigate to: http://localhost:3000
- Check Lakebase guide: verify CU options listed as 1/2/4/8, no mention of 0.5 CU or backup retention
- Check FMAPI Proprietary guide: verify default context length listed as "Long", context length table reordered
- Verify all worked examples still have correct numbers
- Test sidebar navigation between Compute Workloads and AI/ML & Data Services

## Test Results

- `npm run build`: Passes with zero errors
- `pytest`: 1,969 passed, 84 failed (pre-existing), 2 skipped
- All 84 failures are pre-existing structural/coverage tests, unchanged from iteration 1

## Files Changed (Iteration 2 only)

| File | Action |
|------|--------|
| `docs-site/docs/user-guide/lakebase.md` | Fixed CU sizes, removed backup retention, removed 0.5 CU |
| `docs-site/docs/user-guide/fmapi-proprietary.md` | Fixed context length default and descriptions |

## Known Limitations

- $/DBU rates in examples use fallback rates for AWS/us-east-1/Premium. Actual rates vary by cloud/region/tier -- noted with disclaimer in each guide.
- VM costs for DBSQL Classic/Pro use default estimates rather than actual instance pricing.
- FMAPI Proprietary cache_read/cache_write rate types are not covered (rate types exist in pricing bundle but aren't prominently featured in UI).
- Model Serving `num_endpoints` field exists in UI but is not used in backend cost calculations -- intentionally omitted from docs.
