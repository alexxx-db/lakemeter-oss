# Sprint 1 Contract: Getting Started & Introduction Overhaul

## Acceptance Criteria

- [ ] `intro.md` rewritten as compelling landing page with clear value proposition, audience routing (end users, admins, test engineers), and feature highlights
- [ ] `getting-started.md` rewritten as complete 5-minute tutorial using real values: AWS us-east-1 Premium, 3 Jobs workloads with specific instance types and usage patterns, showing exact cost calculations
- [ ] New `user-guide/end-to-end-workflow.md` page covering: create estimate → add workloads → configure → review costs → export Excel → interpret spreadsheet
- [ ] New `user-guide/quick-reference.md` page with table of all 9 workload types, their purpose, key config fields, tier requirements, and when to use each
- [ ] `sidebars.ts` updated to include new pages in logical order
- [ ] All internal links resolve (no broken links)
- [ ] `cd docs-site && npm run build` succeeds with zero errors
- [ ] All field names and options verified against current frontend/backend source code

## Test Plan

- Build verification: `cd docs-site && npm run build` exits 0
- Link verification: no broken link warnings during build
- Content verification: all workload type names match `WorkloadType` enum, all field names match `LineItem` model, all tier restrictions match frontend logic

## Production Readiness Items This Sprint
- None (documentation-only sprint)
