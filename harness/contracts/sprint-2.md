# Sprint 2 Contract: Workload Guides — Compute Workloads (Jobs, All-Purpose, DLT)

## Acceptance Criteria

### Jobs Compute Guide
- [ ] Opens with a real-world scenario ("You're estimating a nightly ETL pipeline...")
- [ ] Includes a fully worked example with actual numbers showing step-by-step cost calculation
- [ ] Configuration table has correct field names, descriptions, and defaults verified against WorkloadForm.tsx
- [ ] Default for Number of Workers is 2 (frontend default), not 0
- [ ] Default for DLT edition is Pro (frontend default), not Core
- [ ] Driver Pricing Tier default is On-Demand, Worker Pricing Tier default is Spot
- [ ] Tips section: when to use Classic vs Serverless, when to enable Photon
- [ ] Common mistakes section
- [ ] Removes generic reused screenshot (`calculator-overview.png`)
- [ ] Defines "DBU" on first use
- [ ] Explains tier restrictions (Serverless requires Premium+) in plain English
- [ ] Removes "Verified Parity" section (internal testing detail, not user-facing)

### All-Purpose Compute Guide
- [ ] Opens with a real-world scenario ("Your data science team needs a shared development cluster...")
- [ ] Includes a worked example with numbers for both Classic and Serverless
- [ ] Configuration table verified against source code
- [ ] Explains Performance mode lock for All-Purpose Serverless clearly
- [ ] Tips: when Serverless saves money vs Classic
- [ ] Common mistakes section
- [ ] Removes generic screenshot
- [ ] Removes "Verified Parity" section

### DLT Pipelines Guide
- [ ] Opens with a real-world scenario ("You're building a streaming data pipeline...")
- [ ] Includes a worked example with numbers
- [ ] Configuration table verified — UI label is "SDP Edition" not "DLT Edition"
- [ ] Explains that DLT Serverless uses Jobs Serverless pricing (all editions same rate)
- [ ] Explains that edition selector is hidden when Serverless is enabled
- [ ] Edition comparison table with practical guidance on when to choose each
- [ ] Tips and common mistakes
- [ ] Removes generic screenshot (`estimate-with-workloads.png`)
- [ ] Removes "Verified Parity" section

### Cross-cutting
- [ ] All three guides use consistent structure and tone matching Sprint 1's style
- [ ] All field names and defaults match WorkloadForm.tsx (lines 448-490)
- [ ] Language is friendly, practical, concise — no jargon without explanation
- [ ] `cd docs-site && npm run build` succeeds with zero errors

## Test Plan
- Docs site build: `cd docs-site && npm run build` — zero errors
- Manual review: each worked example calculation is arithmetically correct
- Field verification: every field name and default matches WorkloadForm.tsx source

## Files to Change
- `docs-site/docs/user-guide/jobs-compute.md` — full rewrite
- `docs-site/docs/user-guide/all-purpose-compute.md` — full rewrite
- `docs-site/docs/user-guide/dlt-pipelines.md` — full rewrite
