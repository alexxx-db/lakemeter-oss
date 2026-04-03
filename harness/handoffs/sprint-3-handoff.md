# Sprint 3 Handoff: Workload Guides — SQL, AI/ML, and Lakebase

## What Was Built

### 6 Workload Guides Rewritten

All 6 guides follow the established Sprint 2 pattern: real-world scenario → worked example with actual numbers → configuration reference → formulas → tips → common mistakes → Excel export.

1. **DBSQL Warehouses** (`docs-site/docs/user-guide/dbsql-warehouses.md`)
   - Scenario: Pro Medium warehouse, 2 clusters, 176 hrs/month
   - Worked example: 48 DBU/hr × 176 = 8,448 DBUs × $0.55 = $4,646.40
   - Classic vs Pro vs Serverless comparison table
   - Warehouse size → DBU/hour reference table (2X-Small to 4X-Large)
   - Removed generic `calculator-overview.png` and `all-workloads-overview.png` references

2. **Model Serving** (`docs-site/docs/user-guide/model-serving.md`)
   - Scenario: A10G 1x GPU, 176 hrs/month
   - Worked example: 20.0 DBU/hr × 176 = 3,520 × $0.07 = $246.40
   - GPU comparison (CPU $12.32 vs T4 $129.11 vs A10G $246.40 for same hours)
   - 14 GPU types table with typical use cases
   - Removed generic screenshot references

3. **Vector Search** (`docs-site/docs/user-guide/vector-search.md`)
   - Scenario: Standard endpoint, 10M vectors, 50 GB storage, 730 hrs
   - Worked example with CEILING function: CEILING(10M/2M) = 5 units × 4.0 = 20.0 DBU/hr
   - Free storage tier calculation: 5 units × 20 GB = 100 GB free
   - Standard vs Storage-Optimized comparison with the same 10M vectors
   - Explained unit boundaries and rounding

4. **FMAPI Databricks** (`docs-site/docs/user-guide/fmapi-databricks.md`)
   - Scenario: Llama 3.3 70B, 50M input + 10M output tokens
   - Worked example: Input 50 × 7.143 × $0.07 = $25.00, Output 10 × 21.429 × $0.07 = $15.00
   - Provisioned throughput comparison ($17,520/mo for 730 hrs)
   - Token-based vs provisioned pricing explained
   - Model list and inference types documented

5. **FMAPI Proprietary** (`docs-site/docs/user-guide/fmapi-proprietary.md`)
   - Scenario: Claude Sonnet 4.5, 5M input + 1M output tokens, global/long context
   - Worked example: Input 5 × 85.714 × $0.07 = $30.00, Output 1 × 321.429 × $0.07 = $22.50
   - Endpoint type comparison (global $52.50 vs in-geo $57.75)
   - Context length comparison (long $52.50 vs short $30.00)
   - All 3 providers and 14 models documented

6. **Lakebase** (`docs-site/docs/user-guide/lakebase.md`)
   - Scenario: 4 CU, 2 nodes, 500 GB, 730 hrs
   - Worked example: Compute $2,336.00 + Storage $172.50 = $2,508.50
   - Small deployment comparison (1 CU, 100 GB = $104.90)
   - Dual-row export (compute + storage) explained clearly
   - DSU conversion (15 DSU/GB × $0.023/DSU)

### Sidebar Restructured

**Before**: Single "Workload Guides" category with all 10 items

**After**: Two categories:
- **Compute Workloads**: Workloads overview, Jobs, All-Purpose, DLT, DBSQL
- **AI/ML & Data Services**: Model Serving, Vector Search, FMAPI Databricks, FMAPI Proprietary, Lakebase

### Workloads Overview Rewritten

Transformed from a flat list of fields into a **decision guide** with:
- Quick decision table: "I need to... → Use this workload"
- Category breakdown (Compute vs AI/ML)
- Pricing tier restrictions table
- Usage input modes (Direct Hours vs Run-Based)

## How to Test

- Start: `cd docs-site && npm run start`
- Navigate to: http://localhost:3000
- Check each guide under "Compute Workloads" and "AI/ML & Data Services" sidebar categories
- Verify the workloads overview "Which Workload Type Do I Need?" decision guide
- Test sidebar navigation between the two new categories
- Verify worked examples have real numbers and step-by-step calculations
- Verify no generic screenshots remain (no calculator-overview.png or all-workloads-overview.png references)

## Test Results

- `npm run build`: Passes with zero errors
- `pytest`: 1,969 passed, 84 failed (pre-existing), 2 skipped
- All 84 failures are pre-existing structural/coverage tests about test file organization, unchanged from Sprint 2

## Verified Data

All pricing numbers in worked examples are verified against the actual pricing bundle JSONs:
- DBSQL: Small=12, Medium=24 DBU/hr; Classic $0.22, Pro $0.55, Serverless $0.70
- Model Serving: CPU=1.0, T4=10.48, A10G 1x=20.0 DBU/hr; SKU $0.07
- Vector Search: Standard=4.0 DBU/hr (2M divisor), Storage-Optimized=18.29 (64M divisor)
- FMAPI DB: llama-3-3-70b input=7.143, output=21.429 DBU/1M; provisioned_scaling=342.857 DBU/hr
- FMAPI Prop: claude-sonnet-4-5 global/long input=85.714, output=321.429 DBU/1M
- Lakebase: DATABASE_SERVERLESS_COMPUTE=$0.40/DBU; storage=15 DSU/GB × $0.023/DSU

## Files Changed

| File | Action |
|------|--------|
| `docs-site/docs/user-guide/dbsql-warehouses.md` | Rewritten |
| `docs-site/docs/user-guide/model-serving.md` | Rewritten |
| `docs-site/docs/user-guide/vector-search.md` | Rewritten |
| `docs-site/docs/user-guide/fmapi-databricks.md` | Rewritten |
| `docs-site/docs/user-guide/fmapi-proprietary.md` | Rewritten |
| `docs-site/docs/user-guide/lakebase.md` | Rewritten |
| `docs-site/docs/user-guide/workloads.md` | Rewritten as decision guide |
| `docs-site/sidebars.ts` | Restructured into Compute / AI-ML categories |
| `harness/contracts/sprint-3.md` | Created |
| `harness/state.json` | Updated |

## Known Limitations

- $/DBU rates in examples use fallback rates for AWS/us-east-1/Premium. Actual rates vary by cloud/region/tier -- noted with disclaimer in each guide.
- VM costs for DBSQL Classic/Pro use default estimates ($0.20/$0.10 per hour) rather than actual instance pricing -- documented in the guide.
- FMAPI Proprietary cache_read/cache_write rate types are not covered (not yet in pricing bundle for most models).
