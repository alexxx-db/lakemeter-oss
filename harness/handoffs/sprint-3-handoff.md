# Sprint 3 Handoff: Workload Guides — SQL, AI/ML, and Lakebase (Iteration 4)

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

## What Was Fixed (Iteration 3)

### FMAPI Proprietary — Added Cache Read/Cache Write Rate Types
- **Added `cache_read` and `cache_write` to rate types table**: The UI shows 4 rate types (Input Token, Output Token, Cache Read, Cache Write) but the docs only documented 2. Added descriptions explaining prompt caching use case.
- **Added prompt caching tip**: Explained when cache_read/cache_write are useful and that Cache Read rates are typically much lower than Input Token rates.
- **Updated info box**: Changed "Add one for input tokens and another for output tokens" to also mention Cache Read/Cache Write line items.

### Model Serving — Added Number of Endpoints Field
- **Added `Number of Endpoints` to config reference**: The UI shows this field (WorkloadForm.tsx line 1603-1612) but the docs omitted it. Added note that the field is for planning purposes and does not multiply cost calculation — each endpoint should be a separate workload entry.

### Lakebase — Removed Duplicate Tip
- **Removed duplicate "Start with 1 CU" tip**: The Tips section had two nearly identical bullets about starting with 1 CU. Merged into a single tip that covers both development use and scaling guidance.

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
- Check FMAPI Proprietary guide: verify rate types table includes Cache Read and Cache Write, prompt caching tip present
- Check Model Serving guide: verify Number of Endpoints field in config reference table
- Check Lakebase guide: verify only one "Start with 1 CU" tip (no duplicate)
- Verify all worked examples still have correct numbers
- Test sidebar navigation between Compute Workloads and AI/ML & Data Services

## Test Results

- `npm run build`: Passes with zero errors
- `pytest`: 1,969 passed, 84 failed (pre-existing), 2 skipped
- All 84 failures are pre-existing structural/coverage tests, unchanged from iteration 1

## Files Changed (Iteration 3 only)

| File | Action |
|------|--------|
| `docs-site/docs/user-guide/fmapi-proprietary.md` | Added cache_read/cache_write rate types, prompt caching tip, updated info box |
| `docs-site/docs/user-guide/model-serving.md` | Added Number of Endpoints to config reference |
| `docs-site/docs/user-guide/lakebase.md` | Removed duplicate "Start with 1 CU" tip |

## What Was Fixed (Iteration 4)

### Model Serving — Removed false run-based usage fields
- **Removed "Run-based usage" fields table**: The Model Serving UI does NOT have run-based input (Runs Per Day, Avg Runtime, Days Per Month). It only has a direct Hours/Month field. The docs incorrectly documented run-based fields that don't exist in the UI.
- **Replaced with "Estimating hours for intermittent usage"**: A tip showing how to manually calculate hours from batch patterns, making it clear users enter the calculated value directly.

### Lakebase — Reframed run-based usage section
- **Reframed "Run-based usage" to "Estimating hours for part-time usage"**: Like Model Serving, Lakebase only has direct Hours/Month input — no run-based toggle. The docs implied run-based UI fields existed. Rewritten to clearly state it's a manual calculation tip.

### FMAPI Databricks — Corrected inference types table
- **Removed "Batch Inference" row**: The FMAPI Databricks rate type dropdown only shows `input_token`, `output_token`, `provisioned_scaling`, and `provisioned_entry`. "Batch Inference" exists in config but is not rendered in the UI dropdown.
- **Fixed group labels**: Changed "Pay-Per-Token" → "Token-based" and "Provisioned Throughput" → "Provisioned" to match the actual `<optgroup>` labels in the UI code (WorkloadForm.tsx lines 1646-1656).

### Workloads Overview — Clarified usage input modes
- **Fixed "Most workloads" claim**: Only 4 of 9 workloads (Jobs, All-Purpose, DLT, DBSQL) support the Run-Based/Direct Hours toggle. Updated to name these explicitly and note that Model Serving, Vector Search, and Lakebase use direct hours only, while FMAPI uses token volume.

### Verification method
All fixes verified by reading WorkloadForm.tsx source code:
- Line 1940: Run-based fields excluded for `show_lakebase_config`, `show_vector_search_mode`, `show_fmapi_config`, and `MODEL_SERVING`
- Lines 2002-2015: Model Serving, Vector Search, and Lakebase get direct hours only
- Lines 1646-1656: FMAPI Databricks rate type dropdown has two optgroups: "Token-based" and "Provisioned"
- Lines 1586-1613: Model Serving config section has GPU Type, Number of Endpoints only (no run-based fields)

## How to Test (Iteration 4)

- Start: `cd docs-site && npm run start`
- Navigate to: http://localhost:3000
- Check Model Serving guide: verify run-based fields table is gone, replaced with "Estimating hours for intermittent usage" tip
- Check Lakebase guide: verify "Run-based usage" is now "Estimating hours for part-time usage"
- Check FMAPI Databricks guide: verify "Inference types in the UI" is now "Rate type groups in the UI" with only Token-based and Provisioned rows (no Batch Inference)
- Check Workloads Overview: verify "Usage input modes" lists specific workloads
- Verify docs build: `cd docs-site && npm run build` — zero errors

## Test Results

- `npm run build`: Passes with zero errors
- `pytest`: 1,969 passed, 84 failed (pre-existing), 2 skipped
- All 84 failures are pre-existing structural/coverage tests, unchanged from iteration 1

## Files Changed (Iteration 4 only)

| File | Action |
|------|--------|
| `docs-site/docs/user-guide/model-serving.md` | Replaced run-based fields table with manual hour calculation tip |
| `docs-site/docs/user-guide/lakebase.md` | Reframed run-based section as manual calculation tip |
| `docs-site/docs/user-guide/fmapi-databricks.md` | Removed Batch Inference row, fixed group labels to match UI |
| `docs-site/docs/user-guide/workloads.md` | Clarified which workloads support run-based vs direct hours |

## What Was Fixed (Iteration 5)

### Model Serving — Removed remaining run-based references
- **Tips section**: Removed "(or run-based)" from the 24/7 vs on-demand tip, since Model Serving only supports direct hours input
- **Common mistakes section**: Changed "Forgetting run-based usage mode" to "Overestimating hours for intermittent usage" — run-based is not available for Model Serving, so the guidance now focuses on correctly calculating and entering hours
- **Excel export table**: Changed "Direct value or run-based calculation" to "Direct hours value" for Hours/Month column

### Lakebase — Removed remaining run-based reference
- **Excel export table**: Changed "Direct value or run-based calculation" to "Direct hours value" for Hours/Month column

### Verification
- `npm run build`: Passes with zero errors
- `pytest`: 1,969 passed, 84 failed (pre-existing), 2 skipped — same as all prior iterations

## Files Changed (Iteration 5 only)

| File | Action |
|------|--------|
| `docs-site/docs/user-guide/model-serving.md` | Removed 3 remaining run-based references in tips, common mistakes, and excel export |
| `docs-site/docs/user-guide/lakebase.md` | Removed 1 remaining run-based reference in excel export table |

## Known Limitations

- $/DBU rates in examples use fallback rates for AWS/us-east-1/Premium. Actual rates vary by cloud/region/tier — noted with disclaimer in each guide.
- VM costs for DBSQL Classic/Pro use default estimates rather than actual instance pricing.
- `batch_inference` rate type exists in the FMAPI Databricks config code but is not rendered in the UI dropdown — not documented.
