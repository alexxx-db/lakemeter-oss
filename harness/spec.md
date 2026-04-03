# Lakemeter Excel Export Parity Fix — Product Spec

## Overview

Lakemeter is a Databricks cost estimation tool. The frontend calculates costs in `costCalculation.ts` and displays them in the UI. The backend independently calculates costs in `backend/app/routes/export/` and writes them to Excel exports. These two calculation paths have diverged, producing mismatched numbers. This project systematically tests EVERY workload type and configuration against the live app, identifies EVERY mismatch, and fixes them ALL so the Excel export is pixel-perfect with the UI.

This is a **tool improvement project** — sprints are improvement areas (workload groups), not new features. The "app" is the existing Lakemeter; the evaluator verifies fixes by comparing live UI numbers against exported Excel cells.

## Test Environment

- **Live app URL**: https://lakemeter-e2e-v2-335310294452632.aws.databricksapps.com
- **Test estimate ID**: `4a3be3ef-1300-458b-890b-755b008e5940`
- **Comparison methodology**: Open browser → read UI costs → download Excel → compare cell-by-cell
- **Tolerance**: $0.01 (matching existing parity test tolerance)

## Code Architecture (Existing)

- **Frontend calculations**: `frontend/src/utils/costCalculation.ts` (571 lines)
- **Frontend pricing lookup**: `frontend/src/utils/pricingBundle.ts` (603 lines)
- **Backend export package**: `backend/app/routes/export/`
  - `pricing.py` — JSON loading, SKU resolution, DBU price lookup
  - `calculations.py` — DBU/hr and hours/month calculations
  - `excel_builder.py` — Workbook assembly orchestrator
  - `excel_item_helpers.py` — Per-item value calculation + storage sub-rows
  - `excel_row_writer.py` — Cell and formula writing (30-column layout)
  - `excel_columns.py` — Column definitions
  - `excel_sections.py` — Totals, summary, legend sections
- **Static pricing JSON**: `backend/static/pricing/` (9 JSON files)
- **Existing parity tests**: `tests/parity/` (Python reimplementation of FE formulas + 9 test files)

## Comparison Points Per Workload

For each workload item, compare these values between UI and Excel:
1. **DBU/hr** — the computed DBU rate per hour
2. **$/DBU** — the price per DBU (from pricing JSON lookup)
3. **Hours/month** — computed from config or direct input
4. **Monthly DBUs** — DBU/hr × Hours/month
5. **Monthly DBU cost** — Monthly DBUs × $/DBU
6. **VM cost** (where applicable) — driver + worker VM costs
7. **Total monthly cost** — DBU cost + VM cost
8. **SKU product type** — correct SKU used for pricing lookup
9. **Configuration details** — instance types, worker counts, sizes displayed correctly

For FMAPI workloads (token-based billing), additionally compare:
- Token quantity (millions)
- DBU per 1M tokens rate
- Total DBUs
- Monthly cost

For storage sub-rows (Vector Search, Lakebase), compare:
- Storage quantity
- Storage rate
- Storage cost

## Features by Sprint

### Sprint 1: JOBS + ALL_PURPOSE Parity (Classic/Photon/Serverless)
- Browser-test all JOBS configurations: classic, photon, serverless (standard + performance mode)
- Browser-test all ALL_PURPOSE configurations: classic, photon, serverless
- Compare DBU/hr, $/DBU, monthly DBU, total cost for each
- Fix all mismatches in backend export code
- Update parity tests to cover any new edge cases found

### Sprint 2: DLT + DBSQL Parity (All Editions/Types/Sizes)
- Browser-test DLT: Core/Pro/Advanced × Classic/Photon/Serverless
- Browser-test DBSQL: Classic/Pro/Serverless × all warehouse sizes (2X-Small through 4X-Large)
- Compare all cost components for each configuration
- Fix all mismatches — pay special attention to DLT edition-specific photon multipliers and DBSQL size-specific DBU rates
- Update parity tests

### Sprint 3: VECTOR_SEARCH + MODEL_SERVING + LAKEBASE Parity
- Browser-test Vector Search: Standard/Storage-Optimized modes, various capacity levels
- Browser-test Model Serving: CPU/T4/A10G/A100 GPU types
- Browser-test Lakebase: various CU sizes, HA node counts, storage amounts
- Compare compute costs AND storage sub-row costs
- Fix all mismatches — special attention to ceiling/rounding in Vector Search, storage DSU calculations in Lakebase
- Update parity tests

### Sprint 4: FMAPI_DATABRICKS + FMAPI_PROPRIETARY Parity (All Models/Providers/Token Types)
- Browser-test FMAPI Databricks: various models × input/output/cache tokens × provisioned modes
- Browser-test FMAPI Proprietary: OpenAI/Anthropic/Google × various models × input/output/cache tokens
- Compare token quantities, DBU/1M rates, total DBUs, monthly costs
- Fix all mismatches — special attention to provider name normalization (Google→GEMINI), fallback rates, context length handling
- Update parity tests

### Sprint 5: Cross-Workload Regression + Excel Formula Audit
- Re-test ALL 9 workload types after all fixes to catch any regressions
- Audit Excel formulas: verify every `=` formula in the spreadsheet produces the correct result (not just the cached value)
- Verify totals row sums all line items correctly
- Verify cost summary section matches
- Run full parity test suite (`pytest tests/parity/`)
- Fix any remaining issues

## Acceptance Criteria (Global)

- Every workload type's Excel export matches UI costs within $0.01 tolerance
- All existing parity tests pass
- New parity tests added for any configurations that were previously untested
- No regressions: fixing one workload must not break another
- Excel formulas (not just cached values) produce correct results when recalculated

## References

- Frontend cost formulas: `frontend/src/utils/costCalculation.ts`
- Backend export: `backend/app/routes/export/`
- Static pricing: `backend/static/pricing/`
- Existing parity tests: `tests/parity/`
- Sprint 10 cross-workload tests: `tests/sprint_10/`
