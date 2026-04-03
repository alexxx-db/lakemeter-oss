# Sprint 4 Contract: AI Assistant, Export, & Calculation Reference

## Acceptance Criteria

### AI Assistant Guide
- [ ] Opens with a real conversation example showing the assistant proposing a workload
- [ ] Documents both Home Mode (Q&A only) and Estimate Mode (full tool use)
- [ ] Lists all 5 agent tools with plain-language descriptions
- [ ] Includes 3+ complete conversation examples with realistic user prompts and AI responses
- [ ] Documents the "Apply to Estimate" and "Confirm Workload" workflows
- [ ] Mentions streaming responses, conversation history limits, and the caution about verifying pricing

### Export Guide
- [ ] Explains the full 30-column Excel layout with grouped descriptions
- [ ] Documents what each section of the exported file contains (header, workloads table, cost summary, legend, assumptions)
- [ ] Covers multi-row workloads (Lakebase, Vector Search storage sub-rows)
- [ ] Includes 2+ use cases (RFP response, internal planning, vendor comparison)
- [ ] Describes formatting: color-coded headers, frozen panes, formulas
- [ ] Documents both single-estimate and bulk export options
- [ ] File naming convention documented

### Calculation Reference
- [ ] 3-4 fully worked examples with real numbers showing step-by-step calculations
- [ ] Example 1: Jobs Classic compute (instance types, DBU rates, hours, VM costs)
- [ ] Example 2: DBSQL Serverless warehouse (size mapping, hours, no VM costs)
- [ ] Example 3: FMAPI token-based pricing (input/output tokens, DBU conversion)
- [ ] Example 4: Classic vs Serverless comparison for the same workload
- [ ] Each example shows the final monthly and annual cost
- [ ] Removes sprint-numbered verification references ("Sprint 1", "Sprint 2")

### FAQ Page
- [ ] Contains 10+ questions a new user would ask
- [ ] Covers: what is Lakemeter, pricing accuracy, cloud/region/tier, workload types, AI assistant, export, discounts, sharing, calculation methodology
- [ ] Each answer is concise (2-4 sentences) with links to detailed pages
- [ ] Added to sidebar under Features category

## Test Plan
- `cd docs-site && npm run build` must succeed with zero errors
- All internal links resolve (Docusaurus throws on broken links)
- Sidebar renders FAQ in the correct position

## Production Readiness Items
- Remove sprint-numbered references from calculation reference
- Ensure all cross-links between the 4 pages work
