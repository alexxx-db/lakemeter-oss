# Sprint 1 Handoff: Getting Started & Introduction Overhaul (Iteration 5 — Final)

## What Was Built

### Pages (created in iterations 1-2, refined in 3-5)
- **`docs-site/docs/intro.md`** — Landing page with audience routing, feature table, quick start
- **`docs-site/docs/user-guide/getting-started.md`** — 5-minute tutorial with real workload examples (Jobs + DBSQL)
- **`docs-site/docs/user-guide/end-to-end-workflow.md`** — Complete create-to-export workflow with cost interpretation
- **`docs-site/docs/user-guide/quick-reference.md`** — Concise reference for all 9 workload types with accurate config fields
- **`docs-site/sidebars.ts`** — Reorganized sidebar into 3 categories (Getting Started, Workload Guides, Features)

## Iteration 5 Fixes (final accuracy pass)

1. **Lakebase CU default: "--" → "1"** — code default is `lakebase_cu: 1` (WorkloadForm.tsx:517)
2. **Lakebase Storage default: "--" → "0"** — code default is `lakebase_storage_gb: 0` (WorkloadForm.tsx:518)
3. **FMAPI Proprietary Rate Type options updated** — added "Batch Inference" and "Provisioned Scaling" to match available code options (WorkloadForm.tsx:1800-1821), with note that availability depends on model

## Accuracy Verification Summary (Iterations 1-5)

All field labels, defaults, and options verified against `WorkloadForm.tsx` source code:

| Area | Status | Verified Against |
|------|--------|-----------------|
| Compute fields (Driver/Worker Instance Type, Worker Count) | ✅ | WorkloadForm.tsx:1132, 1228, 1243 |
| Compute defaults (Spot, 2 workers, 1 run/day, 30 min) | ✅ | WorkloadForm.tsx:486, 499, 481-482 |
| DBSQL (Serverless checkbox, Size, Number of Clusters) | ✅ | WorkloadForm.tsx:1332-1347, 1382, 1394 |
| DBSQL warehouse sizes and DBU rates | ✅ | Fallback values from codebase |
| DLT (SDP Edition label) | ✅ | WorkloadForm.tsx:1314 |
| Model Serving (Endpoint Type, Number of Endpoints) | ✅ | WorkloadForm.tsx:1589, 1603 |
| Vector Search (Vector Search Type, Capacity, Storage) | ✅ | WorkloadForm.tsx:1544, 1555, 1568 |
| FMAPI Databricks (Model, Rate Type, Quantity) | ✅ | WorkloadForm.tsx:1621, 1640, 1662 |
| FMAPI Proprietary (Provider, Model, Endpoint Type, Context Length, Rate Type, Quantity) | ✅ | WorkloadForm.tsx:1703, 1721, 1752, 1764, 1794, 1831 |
| Lakebase (Capacity Units, Number of Nodes, Storage) | ✅ | WorkloadForm.tsx:1861, 1874, 1886 |

## How to Test

1. Build the docs site:
   ```bash
   cd docs-site && npm run build
   ```
2. Serve locally:
   ```bash
   cd docs-site && npm run serve
   ```
3. Verify at http://localhost:3000:
   - **intro page** (`/`): audience routing links resolve, feature table is accurate
   - **getting-started** (`/docs/user-guide/getting-started`): field labels match UI, defaults annotated correctly
   - **end-to-end-workflow** (`/docs/user-guide/end-to-end-workflow`): all steps are logical, cost components table is accurate
   - **quick-reference** (`/docs/user-guide/quick-reference`): all 9 workload types covered, field names match UI, defaults match code
   - All internal links resolve with no 404s

## Build Results

- `npm run build` exit code: **0**
- Errors: **0**
- Warnings: **0**

## Test Results

- `pytest`: **1969 passed**, 84 pre-existing failures (all from `test_workload_coverage.py` coverage structure checks — unrelated to docs), 2 skipped

## Known Limitations

- DBSQL warehouse DBU rates shown are the fallback/default values from the codebase. The actual live API may return different rates for specific cloud/region combinations.
- Model Serving GPU/endpoint types are loaded dynamically from the API; the doc lists representative examples (CPU, T4, A10G).
- DLT edition options (Core, Pro, Advanced) come from the backend API dynamically; the doc lists the fallback defaults.
- FMAPI model lists are dynamic — the docs describe the field structure, not an exhaustive model catalog.

## Files Changed (Iteration 5)

- `docs-site/docs/user-guide/quick-reference.md` (3 fixes: Lakebase defaults, FMAPI Proprietary rate types)
- `harness/handoffs/sprint-1-handoff.md` (updated)
- `harness/state.json` (updated)
