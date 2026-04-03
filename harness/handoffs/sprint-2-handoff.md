# Sprint 2 Handoff: Workload Guides — Compute Workloads (Jobs, All-Purpose, DLT)

## Iteration 4 Changes — Pricing Rate Accuracy, Photon Info Box, Formatting Fix

### Issues fixed in iteration 4:

1. **All-Purpose Serverless example rate corrected: $0.70 → $0.75/DBU**
   - Verified actual `ALL_PURPOSE_SERVERLESS_COMPUTE` rate on AWS us-east-1 Premium is $0.75/DBU
   - Recalculated Serverless comparison: 3,520 DBUs × $0.75 = $2,640.00/month (was $2,464.00)
   - All other example rates already matched actual bundle data ($0.15 Jobs Photon, $0.55 All-Purpose Photon, $0.25 DLT Pro Photon)

2. **Added Photon multiplier info box to All-Purpose guide**
   - Explains that All-Purpose Photon is **2.0x on all clouds** (constant, unlike Jobs/DLT)
   - Notes this is lower than Jobs/DLT multiplier (2.9x AWS / 2.5x Azure, GCP)
   - Parallels the existing info boxes in Jobs and DLT guides

3. **DLT guide formatting fix: Run-Based heading separation**
   - "Run-Based (for scheduled pipelines):" heading was on the same line as "Common values" paragraph
   - Added proper line break for readability

### Complete accuracy verification (all iterations combined):

| Item | Source | Doc accuracy |
|------|--------|-------------|
| Photon multipliers (Jobs/DLT: 2.9x AWS, 2.5x Azure/GCP; All-Purpose: 2.0x all clouds) | `dbu-multipliers.json` | ✅ Correct |
| SKUs (JOBS_COMPUTE, JOBS_COMPUTE_(PHOTON), JOBS_SERVERLESS_COMPUTE, etc.) | `dbu-rates.json` + `costCalculation.ts` | ✅ Correct |
| DLT Serverless uses JOBS_SERVERLESS_COMPUTE | `costCalculation.ts:171` | ✅ Correct |
| All-Purpose Serverless is always Performance mode (2x) | `costCalculation.ts:314` | ✅ Correct |
| All-Purpose Serverless SKU: ALL_PURPOSE_SERVERLESS_COMPUTE | `costCalculation.ts:160` | ✅ Correct |
| Default values (workers=2, days=22, runtime=30, etc.) | `WorkloadForm.tsx` defaults | ✅ Correct |
| SDP Edition default: Pro | `WorkloadForm.tsx:458` | ✅ Correct |
| Worker pricing tier default: Spot | `WorkloadForm.tsx:486` | ✅ Correct |
| Payment Option appears only for AWS Reserved tiers | `WorkloadForm.tsx:1280` | ✅ Correct |
| Worker count minimum: 1 (not 0) | `WorkloadForm.tsx:1246` | ✅ Correct |
| Example $/DBU rates match actual bundle data | `dbu-rates.json` (aws:us-east-1:PREMIUM) | ✅ Correct |
| Jobs Photon rate: $0.15/DBU | JOBS_COMPUTE_(PHOTON) | ✅ Correct |
| All-Purpose Photon rate: $0.55/DBU | ALL_PURPOSE_COMPUTE_(PHOTON) | ✅ Correct |
| All-Purpose Serverless rate: $0.75/DBU | ALL_PURPOSE_SERVERLESS_COMPUTE | ✅ Fixed iter 4 |
| DLT Pro Photon rate: $0.25/DBU | DLT_PRO_COMPUTE_(PHOTON) | ✅ Correct |
| Serverless Mode dropdown: Jobs/DLT only (not All-Purpose) | `WorkloadForm.tsx:1057` | ✅ Correct |
| All-Purpose Serverless shows "Performance Mode" badge | `WorkloadForm.tsx:1058-1062` | ✅ Correct |
| DLT edition hidden when Serverless on | `WorkloadForm.tsx:1312` | ✅ Correct |
| Worked example arithmetic (all three guides) | Manual recalculation | ✅ Correct |

## What Was Built (All iterations combined)

Complete rewrite of three compute workload documentation pages with:
- Real-world scenarios at the top of each page
- Worked examples with verified arithmetic and actual bundle $/DBU rates
- Cloud-specific Photon multiplier info boxes (2.9x/2.5x for Jobs/DLT, 2.0x for All-Purpose)
- Configuration tables verified against `WorkloadForm.tsx` defaults
- Lakemeter UI display names matching the workload type dropdown
- Pricing tier labels matching exact UI text (Spot Instances, On-Demand, 1-Year Reserved, 3-Year Reserved)
- AWS Reserved Payment Option documentation in all three guides
- Tips and Common Mistakes sections
- SKU mapping tables verified against pricing bundle data
- Excel export column reference

## How to Test

1. Start docs site: `cd docs-site && npm run start`
2. Navigate to each guide:
   - http://localhost:3000/user-guide/jobs-compute
   - http://localhost:3000/user-guide/all-purpose-compute
   - http://localhost:3000/user-guide/dlt-pipelines
3. Verify:
   - Each page shows the Lakemeter UI display name
   - Worked examples use correct Photon multipliers
   - All $/DBU rates match actual bundle data for AWS us-east-1 Premium
   - Arithmetic in worked examples is correct
   - All-Purpose Serverless comparison uses $0.75/DBU (total = $2,640.00)
   - All-Purpose has Photon info box explaining constant 2.0x across all clouds
   - DLT "Run-Based" heading is properly separated from "Common values" paragraph
   - Configuration tables show pricing tiers matching UI labels
   - AWS Payment Option tip is present in all three guides
   - All internal links resolve

## Test Results

- `cd docs-site && npm run build`: **SUCCESS** (zero errors, zero warnings)
- `pytest`: **1969 passed**, 84 pre-existing failures (test coverage scaffold), 2 skipped

## Known Limitations

- Example VM prices ($0.192 for m5d.xlarge) are illustrative, not from the pricing bundle (VM costs are fetched on-demand via API, not stored in the bundle). A note clarifies this on each page.
- Screenshots were removed but not replaced with new page-specific screenshots (Visual QA can capture these).
- All-Purpose guide is 203 lines and DLT is 203 lines (slightly over 200-line code target; acceptable for documentation markdown files).

## Files Changed

- `docs-site/docs/user-guide/all-purpose-compute.md` — Fixed Serverless example rate ($0.70→$0.75, recalculated), added Photon info box (199→203 lines)
- `docs-site/docs/user-guide/dlt-pipelines.md` — Fixed Run-Based heading formatting (201→203 lines)
- `harness/handoffs/sprint-2-handoff.md` — Updated (this file)
