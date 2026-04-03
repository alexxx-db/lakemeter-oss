# Sprint 1 Handoff: Getting Started & Introduction Overhaul (Iteration 4)

## What Was Built

### Pages (created in iterations 1-2, refined in 3-4)
- **`docs-site/docs/intro.md`** — Landing page with audience routing, feature table, quick start
- **`docs-site/docs/user-guide/getting-started.md`** — 5-minute tutorial with real workload examples
- **`docs-site/docs/user-guide/end-to-end-workflow.md`** — Complete create-to-export workflow
- **`docs-site/docs/user-guide/quick-reference.md`** — Concise reference for all 9 workload types
- **`docs-site/sidebars.ts`** — Reorganized sidebar into 3 categories

## Iteration 4 Fixes (deep UI label + default verification)

### UI field name accuracy (verified against WorkloadForm.tsx)
1. **"Driver Node Type" → "Driver Instance Type"** — matches UI label at WorkloadForm.tsx:1132
2. **"Worker Node Type" → "Worker Instance Type"** — matches UI label at WorkloadForm.tsx:1228
3. **"Number of Workers" → "Worker Count"** — matches UI label at WorkloadForm.tsx:1243
4. **"Warehouse Size" → "Size"** — matches UI label at WorkloadForm.tsx:1382
5. **"Set Warehouse Type to Serverless" → "Leave the Serverless checkbox checked"** — the UI uses a checkbox toggle (WorkloadForm.tsx:1332-1347), not a dropdown
6. **"DLT Edition" → "SDP Edition"** — matches UI label at WorkloadForm.tsx:1314 (Spark Declarative Pipelines)

### Default value corrections (verified against WorkloadForm.tsx defaults)
7. **Worker Pricing default: "On-demand" → "Spot Instances"** — code default is `worker_pricing_tier: 'spot'` (WorkloadForm.tsx:486,532)
8. **Number of Workers default: 1 → 2** — code default is `num_workers: 2` (WorkloadForm.tsx:499,548)
9. **Runs Per Day default: "--" → "1"** — code default is `runs_per_day: 1` (WorkloadForm.tsx:481,527)
10. **Avg Runtime default: "--" → "30"** — code default is `avg_runtime_minutes: 30` (WorkloadForm.tsx:482,528)

### Getting-started tutorial refinements
11. Added "(the default)" annotations on pricing tier instructions to clarify which values are pre-set
12. Added "(leave unchecked)" clarification for Photon toggle
13. Updated "configure compute" step to reference the Driver Node and Worker Nodes cards as they appear in the UI

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
   - Field names match the actual Lakemeter UI: "Driver Instance Type", "Worker Instance Type", "Worker Count", "Size", "SDP Edition"
   - Defaults match: Worker Pricing = Spot Instances, Worker Count = 2, Runs Per Day = 1, Avg Runtime = 30, Days Per Month = 22
   - DBSQL shows "Serverless" as a checkbox description, not a warehouse type dropdown option
   - DBSQL Size default shows "Small (12 DBU/hr)"
   - DBSQL warehouse DBU rates table is correct: 2X-Small=4, X-Small=6, Small=12, Medium=24, Large=40, X-Large=80, 2X-Large=144, 3X-Large=272, 4X-Large=528

4. Navigate to http://localhost:3000/docs/user-guide/getting-started and verify:
   - Step 5 references "Driver Node" and "Worker Nodes" cards
   - Field labels match: "Driver Instance Type", "Worker Instance Type", "Worker Count"
   - Pricing tier instructions note "(the default)" for pre-set values
   - DBSQL step says "Leave the Serverless checkbox checked"
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
- DLT edition options (Core, Pro, Advanced) come from the backend API dynamically; the doc lists the fallback defaults.

## Files Changed

- `docs-site/docs/user-guide/quick-reference.md` (10 field name and default fixes)
- `docs-site/docs/user-guide/getting-started.md` (6 field name and UI interaction fixes)
- `harness/handoffs/sprint-1-handoff.md` (updated)
- `harness/state.json` (updated)
