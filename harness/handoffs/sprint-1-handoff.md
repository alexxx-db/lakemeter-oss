# Sprint 1 Handoff: Getting Started & Introduction Overhaul (Iteration 3)

## What Was Built

### Pages (unchanged from iteration 1-2)
- **`docs-site/docs/intro.md`** — Landing page with audience routing, feature table, quick start
- **`docs-site/docs/user-guide/getting-started.md`** — 5-minute tutorial with real workload examples
- **`docs-site/docs/user-guide/end-to-end-workflow.md`** — Complete create-to-export workflow
- **`docs-site/docs/user-guide/quick-reference.md`** — Concise reference for all 9 workload types
- **`docs-site/sidebars.ts`** — Reorganized sidebar into 3 categories

## Iteration 3 Fixes (deep accuracy verification against source code)

### CRITICAL: DBSQL warehouse DBU rates table (5 wrong values)
Verified against `backend/app/routes/export/calculations.py:103-104` and `backend/app/main.py:841-842`:
1. **X-Small**: 8 → **6** DBU/hr
2. **X-Large**: 64 → **80** DBU/hr
3. **2X-Large**: 128 → **144** DBU/hr
4. **3X-Large**: 256 → **272** DBU/hr
5. **4X-Large**: 512 → **528** DBU/hr

### Days Per Month default
- Was: 30. Corrected to: **22** (verified against `WorkloadForm.tsx` lines 483, 529 default initialization)

### Lakebase CU options
- Was: "0.5, 1-32 autoscaling, 36-112 fixed". Corrected to: **1, 2, 4, or 8 CU** (verified against `WorkloadForm.tsx` lines 1867-1871 — dropdown with 4 options)

### Model Serving field names
- Renamed "GPU Type" → **"Endpoint Type"** (matches UI label at `WorkloadForm.tsx:1589`)
- Added **"Number of Endpoints"** field (exists in form at `WorkloadForm.tsx:1603-1611`)
- Updated cost formula to reflect endpoints multiplier

### Vector Search field accuracy
- Updated mode descriptions to include specific DBU rates from UI: "Standard (4 DBU/hr per 2M vectors)" and "Storage Optimized (18.29 DBU/hr per 64M vectors)" (from `WorkloadForm.tsx:1550-1551`)
- Corrected field names to match UI labels: "Vector Search Type", "Capacity (M vectors)"
- Added storage pricing note: "20 GB free per endpoint unit, $0.023/GB/mo above" (from `WorkloadForm.tsx:1579`)

### FMAPI Databricks description
- Clarified rate types into "Token-based" and "Provisioned" groups matching the UI optgroup structure
- Clarified quantity field: tokens in millions for token-based, hours/month for provisioned

## How to Test

1. Build the docs site:
   ```bash
   cd docs-site && npm run build
   ```
2. Serve locally:
   ```bash
   cd docs-site && npm run serve
   ```
3. Navigate to http://localhost:3000/docs/user-guide/quick-reference and verify:
   - DBSQL warehouse sizes table shows correct DBU/hr rates: 2X-Small=4, X-Small=6, Small=12, Medium=24, Large=40, X-Large=80, 2X-Large=144, 3X-Large=272, 4X-Large=528
   - Jobs Days Per Month default shows 22
   - Lakebase shows "Capacity Units (CU)" with "1, 2, 4, or 8 CU"
   - Model Serving shows "Endpoint Type" and "Number of Endpoints" fields
   - Vector Search shows specific DBU rates and storage pricing note
   - FMAPI Databricks shows token-based vs provisioned distinction
   - All internal links resolve

## Build Results

- `npm run build` exit code: **0**
- Errors: **0**
- Warnings: **0**

## Test Results

- `pytest`: **1969 passed**, 84 pre-existing failures (all from `test_workload_coverage.py` coverage structure checks — unrelated to docs), 2 skipped

## Known Limitations

- DBSQL warehouse DBU rates shown are the fallback/default values from the codebase. The actual live API may return different rates for specific cloud/region combinations, but these are the canonical values.
- Model Serving GPU/endpoint types are loaded dynamically from the API; the doc lists representative examples (CPU, T4, A10G) rather than exhaustive options.

## Files Changed

- `docs-site/docs/user-guide/quick-reference.md` (8 accuracy fixes)
- `harness/state.json` (updated)
- `harness/handoffs/sprint-1-handoff.md` (updated)
