# Sprint 1 Handoff: Getting Started & Introduction Overhaul (Iteration 2)

## What Was Built

### Rewritten pages (2)
- **`docs-site/docs/intro.md`** — Complete rewrite as a compelling landing page with:
  - Clear value proposition ("Build accurate Databricks cost estimates in minutes, not days")
  - Audience routing: SAs/SEs, Data Engineers/Platform Teams, Administrators — each with targeted "Start here" links
  - Feature summary table organized by category (Compute, SQL, AI/ML, Data Services)
  - Key capabilities list with descriptions
  - Quick start steps

- **`docs-site/docs/user-guide/getting-started.md`** — Rewritten as a concrete 5-minute tutorial:
  - Creates a real estimate: "Q4 Data Platform - AWS" on AWS us-east-1 Premium
  - Two fully configured workloads with real values: ETL Pipeline (Jobs Classic, 4 workers, m5d.xlarge, 2 runs/day x 45 min) and Analytics Warehouse (DBSQL Serverless, Small, 220 hrs/month)
  - "What the numbers mean" explanations after each workload showing how hours, DBUs, and costs relate
  - Export walkthrough with description of Excel file contents
  - "What to try next" section linking to Quick Reference, AI Assistant, and End-to-End Workflow

### New pages (2)
- **`docs-site/docs/user-guide/end-to-end-workflow.md`** — Complete create-to-interpret workflow:
  - Planning section with tier comparison table (verified against source code tier restrictions)
  - Step-by-step: create estimate, add workloads, configure, review costs, export, interpret report
  - Cost component breakdown table (DBU, VM, Token, Storage)
  - Quick optimization checks (spot, reserved, serverless, Photon)
  - Excel report interpretation guide with column descriptions
  - Use-case-specific guidance (RFP, budgeting, vendor comparison, architecture review)
  - Iteration and refinement patterns

- **`docs-site/docs/user-guide/quick-reference.md`** — Concise reference card:
  - All 9 workload types with description, use case, and minimum tier requirement
  - Key terms glossary (DBU, SKU, Photon, Serverless, Classic)
  - Configuration tables for every workload type with fields, descriptions, and defaults
  - DBSQL warehouse sizes with DBU/hr rates
  - Cost formula summary table for every workload type

### Updated config (1)
- **`docs-site/sidebars.ts`** — Reorganized User Guide sidebar into 3 logical categories:
  - "Getting Started" (overview, tutorial, workflow, quick reference, creating estimates)
  - "Workload Guides" (workloads overview + 9 individual guides)
  - "Features" (AI assistant, exporting, calculation reference)

## Iteration 2 Fixes (accuracy verification against source code)

1. **Days Per Month default**: Getting-started tutorial now notes that the default is 22 business days and explains why we override to 30 for a daily ETL workload (verified against `WorkloadForm.tsx` default of 22 and `backend/app/schemas/line_item.py` default of 22)
2. **DBSQL tier restriction**: End-to-end workflow tier table updated from "DBSQL (Classic)" to "DBSQL (Classic, Pro)" for Standard tier (verified against `WorkloadForm.tsx` `isWorkloadAvailableForTier` — only SERVERLESS type is Premium-only, Classic and Pro are both available on Standard)
3. **Quick reference DBSQL min tier**: Updated from "Standard (Classic), Premium (Serverless)" to "Standard (Classic/Pro), Premium (Serverless)" to match actual tier restrictions

## How to Test

1. Build the docs site:
   ```bash
   cd docs-site && npm run build
   ```
2. Serve locally:
   ```bash
   cd docs-site && npm run serve
   ```
3. Navigate to http://localhost:3000/docs/ and verify:
   - Landing page (intro) loads with audience routing and feature table
   - "5-Minute Tutorial" has real numbers (AWS us-east-1, m5d.xlarge, etc.) and correctly notes the 22-day default override
   - "End-to-End Workflow" tier table shows DBSQL (Classic, Pro) for Standard
   - "Quick Reference" shows DBSQL as "Standard (Classic/Pro), Premium (Serverless)"
   - Sidebar shows 3 categories: Getting Started, Workload Guides, Features
   - All internal links resolve (click through every link on the new/modified pages)

## Build Results

- `npm run build` exit code: **0**
- Errors: **0**
- Warnings: **0**

## Test Results

- `pytest` (excluding pre-existing integration validation failures): **1907 passed**, 5 pre-existing failures, 2 skipped
- Pre-existing failures are all from old sprint-numbered test file references (unrelated to docs):
  - `test_regression_s10.py` — references `pyproject.toml` addopts for ai_assistant tests
  - `test_jobs_bugs.py` — references old `sprint_1/test_jobs_export_integration.py` path

## Known Limitations

- Getting-started tutorial uses example values (m5d.xlarge, etc.) that are accurate for the app but not verified against a specific live pricing snapshot — actual costs will depend on current DBU rates
- Quick reference DBSQL warehouse size table (4-512 DBU/hr) is based on backend source code patterns; specific rates may vary by cloud/region
- Screenshots are not included (per spec, generic reused screenshots were removed; page-specific screenshots will be captured by Visual QA agent)

## Files Changed

- `docs-site/docs/intro.md` (rewritten in iter 1)
- `docs-site/docs/user-guide/getting-started.md` (rewritten in iter 1, accuracy fix in iter 2)
- `docs-site/docs/user-guide/end-to-end-workflow.md` (new in iter 1, accuracy fix in iter 2)
- `docs-site/docs/user-guide/quick-reference.md` (new in iter 1, accuracy fix in iter 2)
- `docs-site/sidebars.ts` (updated in iter 1)
- `harness/contracts/sprint-1.md` (iter 1)
- `harness/handoffs/sprint-1-handoff.md` (updated in iter 2)
