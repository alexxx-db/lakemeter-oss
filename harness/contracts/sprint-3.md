# Sprint 3 Contract: Workload Guides — SQL, AI/ML, and Lakebase

## Acceptance Criteria

- [ ] DBSQL guide rewritten with real-world scenario, worked example with actual numbers, configuration reference verified against source, tips, common mistakes
- [ ] Model Serving guide rewritten with same treatment
- [ ] Vector Search guide rewritten with same treatment, CEILING function explained clearly
- [ ] FMAPI Databricks guide rewritten with same treatment, token vs provisioned pricing explained
- [ ] FMAPI Proprietary guide rewritten with same treatment, all 3 providers documented with model lists
- [ ] Lakebase guide rewritten with same treatment, dual-row export (compute + storage) explained
- [ ] Sidebar restructured: "Compute Workloads" (workloads overview, Jobs, All-Purpose, DLT, DBSQL) and "AI/ML & Data Services" (Model Serving, Vector Search, FMAPI Databricks, FMAPI Proprietary, Lakebase)
- [ ] Workloads overview rewritten as a decision guide ("Which workload type do I need?")
- [ ] All field names verified against WorkloadForm.tsx
- [ ] All $/DBU rates verified against pricing bundle JSONs
- [ ] All formulas verified against costCalculation.ts
- [ ] Generic reused screenshots removed (calculator-overview.png, all-workloads-overview.png references)
- [ ] Docs site builds cleanly: `cd docs-site && npm run build` passes
- [ ] Each guide follows the established Sprint 2 pattern: scenario → worked example → config reference → formula → tips → common mistakes → Excel export

## Format Pattern (from Sprint 2)

Each guide follows this structure:
1. UI name callout (> **Lakemeter UI name:** ...)
2. When to use — context and use case
3. Real-world example with specific numbers
4. Step-by-step calculation breakdown
5. Configuration reference table
6. How costs are calculated (formula boxes)
7. SKU mapping
8. Tips (3-4 bullets)
9. Common mistakes (3-4 bullets)
10. Excel export columns

## Verified Pricing Data for Examples

- DBSQL: Small=12 DBU/hr, Medium=24 DBU/hr; Classic $0.22, Pro $0.55, Serverless $0.70
- Model Serving: CPU=1.0, T4=10.48, A10G 1x=20.0 DBU/hr; SKU $0.07
- Vector Search: Standard=4.0 DBU/hr (divisor 2M), Storage-Optimized=18.29 (divisor 64M)
- FMAPI DB: llama-3-3-70b input=7.143, output=21.429 DBU/1M; provisioned_scaling=342.857 DBU/hr
- FMAPI Prop: claude-sonnet-4-5 global/long input=85.714, output=321.429 DBU/1M
- Lakebase: DATABASE_SERVERLESS_COMPUTE=$0.40/DBU; storage=15 DSU/GB × $0.023/DSU
- SERVERLESS_REAL_TIME_INFERENCE: $0.07/DBU

## Test Plan

- Docs site build: `cd docs-site && npm run build` — zero errors
- Existing pytest suite: all tests must still pass
- Manual verification: all internal links resolve, no broken references
