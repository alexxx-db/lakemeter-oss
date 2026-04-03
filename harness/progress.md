# Lakemeter Excel Export Parity Fix — Progress

## Quality Target: 9.0/10

## Sprint Status

| Sprint | Feature | Status | Score | Tests | Iterations | Decision |
|--------|---------|--------|-------|-------|------------|----------|
| 1 | JOBS + ALL_PURPOSE Parity | PENDING | - | - | 0 | - |
| 2 | DLT + DBSQL Parity | PENDING | - | - | 0 | - |
| 3 | VECTOR_SEARCH + MODEL_SERVING + LAKEBASE Parity | PENDING | - | - | 0 | - |
| 4 | FMAPI_DATABRICKS + FMAPI_PROPRIETARY Parity | PENDING | - | - | 0 | - |
| 5 | Cross-Workload Regression + Excel Formula Audit | PENDING | - | - | 0 | - |

## Approach

This is a **tool improvement project**. Each sprint:
1. Opens the live app in browser, reads UI costs for the workload group
2. Downloads Excel export from the same estimate
3. Compares every number cell-by-cell (DBU/hr, $/DBU, monthly DBU, VM cost, total cost)
4. Traces mismatches to backend export code and fixes them
5. Runs parity tests to verify fixes and catch regressions

## Key Files
- Frontend calculations: `frontend/src/utils/costCalculation.ts`
- Backend export: `backend/app/routes/export/` (pricing.py, calculations.py, excel_builder.py, excel_item_helpers.py, excel_row_writer.py)
- Static pricing JSON: `backend/static/pricing/`
- Parity tests: `tests/parity/`
- Live app: https://lakemeter-e2e-v2-335310294452632.aws.databricksapps.com
- Test estimate: `4a3be3ef-1300-458b-890b-755b008e5940`
