# Sprint 2 Handoff: Workload Guides — Compute Workloads (Jobs, All-Purpose, DLT)

## What Was Built

Complete rewrite of three compute workload documentation pages:

### Jobs Compute (`docs-site/docs/user-guide/jobs-compute.md`)
- Added real-world scenario: nightly ETL pipeline (2 runs/day, 45 min, 4 workers, Photon)
- Added step-by-step worked example with DBU, VM, and total cost calculations
- Updated configuration reference with correct defaults from WorkloadForm.tsx
- Added Tips section (Classic vs Serverless, Photon, Spot pricing, Days Per Month)
- Added Common Mistakes section (0 workers, Photon doubling, Performance mode for ETL)
- Removed generic reused screenshot (`calculator-overview.png`)
- Removed internal "Verified Parity" section
- Defined DBU and tier restrictions in plain language

### All-Purpose Compute (`docs-site/docs/user-guide/all-purpose-compute.md`)
- Added real-world scenario: data science team shared cluster (8 hrs/day, 22 days)
- Added worked examples for BOTH Classic and Serverless showing why Classic wins for long usage
- Documented Performance mode lock for All-Purpose Serverless (no Standard option)
- Updated configuration reference with correct defaults
- Added comparison section with total cost comparison
- Added Tips section (when Serverless saves money, Reserved pricing for 24/7)
- Added Common Mistakes section (0 hours, expecting Standard mode)
- Removed generic screenshot and Verified Parity section

### DLT Pipelines (`docs-site/docs/user-guide/dlt-pipelines.md`)
- Added real-world scenario: 24/7 streaming CDC pipeline with Pro edition
- Added step-by-step worked example with Pro Photon pricing
- Updated edition selector label to "SDP Edition" matching UI
- Documented that edition selector is hidden when Serverless is enabled
- Explained that all DLT Serverless editions use same `JOBS_SERVERLESS_COMPUTE` pricing
- Added practical edition comparison table with "when to pick each" guidance
- Added Tips section (edition-independent Serverless pricing, continuous vs scheduled)
- Added Common Mistakes section (choosing Advanced unnecessarily, 730 hrs for batch)
- Removed generic screenshot (`estimate-with-workloads.png`) and Verified Parity section

### Key accuracy fixes from source code verification
- **Number of Workers default**: Changed from 0 to 2 (matches WorkloadForm.tsx line 456)
- **DLT Edition default**: Changed from Core to Pro (matches WorkloadForm.tsx line 458)
- **Worker Pricing Tier default**: Confirmed Spot (matches WorkloadForm.tsx line 486)
- **SDP Edition label**: Changed from "DLT Edition" to "SDP Edition" (matches UI label at line 1314)
- **All-Purpose Serverless**: Confirmed forced Performance mode with "Performance Mode" badge (lines 1057-1063)
- **DLT edition hidden on Serverless**: Confirmed via `!form.serverless_enabled` guard (line 1312)

## How to Test

1. Start docs site: `cd docs-site && npm run start`
2. Navigate to each guide:
   - http://localhost:3000/user-guide/jobs-compute
   - http://localhost:3000/user-guide/all-purpose-compute
   - http://localhost:3000/user-guide/dlt-pipelines
3. Verify:
   - Each page opens with a real-world scenario
   - Worked examples have correct arithmetic
   - Configuration tables show field names matching the live app
   - Tips and Common Mistakes sections are present
   - No generic screenshots appear
   - All internal links resolve

## Test Results

- `cd docs-site && npm run build`: **SUCCESS** (zero errors, zero warnings)
- `pytest`: **1969 passed**, 84 pre-existing failures (test coverage scaffold, unrelated to docs), 2 skipped

## Known Limitations

- Example $/DBU rates and VM prices in worked examples are illustrative, not real-time. A note clarifies this on each page.
- Screenshots were removed but not replaced with new page-specific screenshots (Visual QA can capture these).

## Files Changed

- `docs-site/docs/user-guide/jobs-compute.md` — full rewrite (147 → 161 lines)
- `docs-site/docs/user-guide/all-purpose-compute.md` — full rewrite (161 → 167 lines)
- `docs-site/docs/user-guide/dlt-pipelines.md` — full rewrite (194 → 189 lines)
- `harness/contracts/sprint-2.md` — new (sprint contract)
- `harness/handoffs/sprint-2-handoff.md` — new (this file)
