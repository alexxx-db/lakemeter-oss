# Sprint 2 Handoff: Workload Guides — Compute Workloads (Jobs, All-Purpose, DLT)

## Iteration 2 Changes — Photon Multiplier Accuracy Fix

**Critical accuracy issue found and fixed:** The Photon multiplier was incorrectly documented as "2x" across all three guides. Actual values from the pricing bundle (`dbu-multipliers.json`):

| Cloud | Jobs Photon | All-Purpose Photon | DLT Photon |
|-------|-------------|-------------------|------------|
| AWS | **2.9x** | 2.0x | **2.9x** |
| Azure | **2.5x** | 2.0x | **2.5x** |
| GCP | **2.5x** | 2.0x | **2.5x** |

All-Purpose was already correct at 2.0x. Jobs and DLT guides had incorrect "2x" references throughout.

### Specific fixes in Jobs guide (`jobs-compute.md`):
- Worked example: Photon multiplier changed from 2.0 to 2.9 (AWS), recalculated DBU/Hour from 10.0 to 14.5, Monthly DBUs from 450 to 652.5, DBU Cost from $135.00 to $97.88, Total from $156.06 to $118.94
- Added info callout explaining cloud-specific Photon multipliers
- Config reference: Updated Photon description to show cloud-specific rates
- Classic formula notes: Updated from "2.0 when Photon is on" to cloud-specific values
- Serverless formula: Changed from "x 2" to "x Photon Multiplier" with cloud-specific note
- Tips: Updated Photon tip with correct multiplier ranges
- Common mistakes: Updated "doubles DBUs" to "increases DBUs" with correct values

### Specific fixes in DLT guide (`dlt-pipelines.md`):
- Worked example: Photon multiplier changed from 2.0 to 2.9 (AWS), recalculated DBU/Hour from 8.0 to 11.6, Monthly DBUs from 5,840 to 8,468, DBU Cost from $2,219.20 to $2,117.00, Total from $2,779.84 to $2,677.64
- Added info callout explaining cloud-specific Photon multipliers
- Config reference: Updated Photon description to show cloud-specific rates
- Classic formula notes: Added cloud-specific multiplier information
- Serverless formula: Changed from "x 2" to "x Photon Multiplier" with cloud-specific note
- Tips: Updated Photon tip with correct multiplier ranges
- Common mistakes: Updated with correct multiplier values

### All-Purpose guide — no changes needed
- Photon multiplier is correctly 2.0x on all clouds
- Serverless formula correctly shows "2x Photon × 2x Performance = 4x"

## What Was Built (Iteration 1 + 2 combined)

Complete rewrite of three compute workload documentation pages with:
- Real-world scenarios at the top of each page
- Worked examples with correct arithmetic and cloud-specific Photon multipliers
- Configuration tables verified against `WorkloadForm.tsx` defaults
- Tips and Common Mistakes sections
- SKU mapping tables
- Excel export column reference

## How to Test

1. Start docs site: `cd docs-site && npm run start`
2. Navigate to each guide:
   - http://localhost:3000/user-guide/jobs-compute
   - http://localhost:3000/user-guide/all-purpose-compute
   - http://localhost:3000/user-guide/dlt-pipelines
3. Verify:
   - Each page opens with a real-world scenario
   - Worked examples use correct Photon multipliers (2.9x for Jobs/DLT on AWS, 2.0x for All-Purpose)
   - Arithmetic in worked examples is correct
   - Configuration tables show field names matching the live app
   - Info callouts explain cloud-specific Photon variation
   - No generic screenshots appear
   - All internal links resolve

## Test Results

- `cd docs-site && npm run build`: **SUCCESS** (zero errors, zero warnings)
- `pytest`: **1969 passed**, 85 pre-existing failures (84 test coverage scaffold + 1 missing pyproject.toml), 2 skipped

## Known Limitations

- Example $/DBU rates and VM prices in worked examples are illustrative, not real-time. A note clarifies this on each page.
- Screenshots were removed but not replaced with new page-specific screenshots (Visual QA can capture these).

## Files Changed

- `docs-site/docs/user-guide/jobs-compute.md` — Photon multiplier fix (161 → 191 lines)
- `docs-site/docs/user-guide/dlt-pipelines.md` — Photon multiplier fix (199 → 202 lines)
- `docs-site/docs/user-guide/all-purpose-compute.md` — unchanged (193 lines, already correct)
- `harness/handoffs/sprint-2-handoff.md` — updated (this file)
