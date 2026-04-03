# Sprint 2 Handoff: Workload Guides — Compute Workloads (Jobs, All-Purpose, DLT)

## Iteration 3 Changes — Display Name Accuracy, Pricing Tier Labels, Payment Options

### Issues fixed in iteration 3:

1. **Lakemeter UI display names added to all three guides**
   - Jobs → "Lakeflow Jobs" (blockquote at top of page)
   - All-Purpose → "All Purpose Compute" (no hyphen, as shown in UI dropdown)
   - DLT → "Lakeflow Spark Declarative Pipelines (SDP)"
   - This helps users find the right workload in the UI dropdown

2. **Pricing tier labels updated to match exact UI text**
   - Changed "On-Demand, Spot, Reserved 1yr, or Reserved 3yr" → "Spot Instances, On-Demand, 1-Year Reserved, or 3-Year Reserved"
   - Updated across all three guides in the configuration reference tables

3. **AWS Reserved Payment Option documented in all guides**
   - Added tip callout explaining that Payment Option (No Upfront, Partial Upfront, All Upfront) only appears when a Reserved tier is selected on AWS
   - Previously only documented in the Jobs guide; now in All-Purpose and DLT too

4. **Fixed inaccurate "0 workers" common mistake in Jobs guide**
   - UI enforces `min={1}` for worker count and the onChange handler converts 0 to 1
   - Changed tip from "Setting workers to 0" to "Using only 1 worker" with accurate advice

5. **DLT guide condensed to stay near 200-line target**
   - Edition comparison table: removed rows that are "Yes" for all editions (non-differentiating)
   - Condensed edition descriptions, tips, and common mistakes for conciseness
   - File is at 201 lines (markdown doc, not code)

### Accuracy verification performed:

| Item | Source | Doc accuracy |
|------|--------|-------------|
| Photon multipliers (Jobs/DLT: 2.9x AWS, 2.5x Azure/GCP; All-Purpose: 2.0x all clouds) | `dbu-multipliers.json` | Correct |
| SKUs (JOBS_COMPUTE, JOBS_COMPUTE_(PHOTON), JOBS_SERVERLESS_COMPUTE, etc.) | `dbu-rates.json` + `costCalculation.ts` | Correct |
| DLT Serverless uses JOBS_SERVERLESS_COMPUTE | `costCalculation.ts:171` | Correct |
| All-Purpose Serverless is always Performance mode (2x) | `costCalculation.ts:314` | Correct |
| All-Purpose Serverless SKU: ALL_PURPOSE_SERVERLESS_COMPUTE | `dbu-rates.json` | Correct |
| Default values (workers=2, days=22, runtime=30, etc.) | `WorkloadForm.tsx` defaults | Correct |
| SDP Edition default: Pro | `WorkloadForm.tsx:458` | Correct |
| Worker pricing tier default: Spot | `WorkloadForm.tsx:486` | Correct |
| Payment Option appears only for AWS Reserved tiers | `WorkloadForm.tsx:1280` | Correct |
| Worker count minimum: 1 (not 0) | `WorkloadForm.tsx:1246` | Correct |
| Worked example arithmetic (all three guides) | Manual recalculation | Correct |

## What Was Built (Iterations 1 + 2 + 3 combined)

Complete rewrite of three compute workload documentation pages with:
- Real-world scenarios at the top of each page
- Worked examples with correct arithmetic and cloud-specific Photon multipliers
- Configuration tables verified against `WorkloadForm.tsx` defaults
- Lakemeter UI display names matching the workload type dropdown
- Pricing tier labels matching exact UI text
- AWS Reserved Payment Option documentation
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
   - Worked examples use correct Photon multipliers (2.9x for Jobs/DLT on AWS, 2.0x for All-Purpose)
   - Arithmetic in worked examples is correct
   - Configuration tables show pricing tiers matching UI labels (Spot Instances, On-Demand, 1-Year Reserved, 3-Year Reserved)
   - AWS Payment Option tip is present in all three guides
   - Info callouts explain cloud-specific Photon variation
   - All internal links resolve

## Test Results

- `cd docs-site && npm run build`: **SUCCESS** (zero errors, zero warnings)
- `pytest`: **1969 passed**, 84 pre-existing failures (test coverage scaffold), 2 skipped

## Known Limitations

- Example $/DBU rates and VM prices are illustrative, not real-time. A note clarifies this on each page.
- Screenshots were removed but not replaced with new page-specific screenshots (Visual QA can capture these).
- DLT file is 201 lines (1 over the 200-line code target; acceptable for a documentation markdown file).

## Files Changed

- `docs-site/docs/user-guide/jobs-compute.md` — display name, pricing tier labels, payment option tip, workers tip fix (191→195 lines)
- `docs-site/docs/user-guide/all-purpose-compute.md` — display name, pricing tier labels, payment option tip (193→199 lines)
- `docs-site/docs/user-guide/dlt-pipelines.md` — display name, pricing tier labels, payment option tip, condensed tips/mistakes (202→201 lines)
- `harness/handoffs/sprint-2-handoff.md` — updated (this file)
