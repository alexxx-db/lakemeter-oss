# Sprint 4 Handoff: AI Assistant, Export, & Calculation Reference

## What Was Built

### AI Assistant Guide (`docs-site/docs/user-guide/ai-assistant.md`)
- Complete rewrite with 4 concrete conversation examples:
  1. Creating a single workload from natural language
  2. Generating a complete multi-workload estimate
  3. Optimizing an existing estimate
  4. Getting a GenAI architecture recommendation (RAG chatbot)
- Documents all 5 agent tools in a reference table
- Explains both Home Mode (Q&A) and Estimate Mode (full tool use)
- Documents the Confirm/Edit/Cancel workflow for AI-proposed workloads
- Notes on conversation history limits and streaming

### Export Guide (`docs-site/docs/user-guide/exporting.md`)
- Complete rewrite documenting the full Excel export structure:
  - 6 sections: Header, Workloads Table, Multi-Row Workloads, Cost Summary, Legend, Assumptions
  - 30-column layout grouped by purpose (Identity, VM Config, Usage, Tokens, DBU Costs, VM Costs, Totals)
  - Color-coded header explanation (orange, blue, cyan, pink, green, purple)
  - Formatting: frozen panes, formulas, currency formatting, landscape orientation
- Documents both single-estimate and bulk export options
- File naming convention: `Databricks_Estimate_{name}_{YYYYMMDD}.xlsx`
- 4 use cases: RFP response, internal planning, vendor comparison, cost modeling

### Calculation Reference (`docs-site/docs/user-guide/calculation-reference.md`)
- Complete rewrite with 4 fully worked examples using real pricing data:
  1. **Jobs Classic with Photon**: i3.xlarge × 4 workers, run-based hours → $252.45/mo
  2. **DBSQL Serverless**: Medium warehouse, business hours → $2,956.80/mo
  3. **FMAPI Token-Based**: Llama 3.1 8B, 50M input + 10M output tokens → $12.00/mo
  4. **Classic vs Serverless Comparison**: Same workload both ways, showing 51% savings
- All sprint-numbered verification references removed (was "Verified by N parity tests (Sprint X)")
- Clean formula reference section for all 9 workload types
- Cross-link to Export guide for column layout details

### FAQ Page (`docs-site/docs/user-guide/faq.md`) — NEW
- 13 questions across 5 categories: General, Configuration, AI Assistant, Export & Pricing, Troubleshooting
- Covers: what is Lakemeter, pricing accuracy, cloud/region/tier, workload type selection, Classic vs Serverless, AI capabilities, export format, discounts, multi-row workloads, DBU rates, grayed-out workloads, cost verification
- Every answer links to the relevant detailed page
- Added to sidebar under Features category

### Sidebar Update (`docs-site/sidebars.ts`)
- Added `user-guide/faq` to the Features category

## How to Test

1. Start docs dev server: `cd docs-site && npm run start`
2. Navigate to each page and verify:
   - **AI Assistant** (`/user-guide/ai-assistant`): 4 conversation examples render correctly, tool table is readable
   - **Exporting** (`/user-guide/exporting`): Column group table, multi-row explanation, use cases section
   - **Calculation Reference** (`/user-guide/calculation-reference`): 4 worked examples with step-by-step math, side-by-side comparison table
   - **FAQ** (`/user-guide/faq`): 13 Q&A items, all internal links resolve, workload type selection table
3. Check sidebar: FAQ appears under Features after Calculation Reference
4. Verify cross-links: FAQ links to all workload guides, Calculation Reference links to Export guide

## Test Results

- `npm run build`: **PASS** (zero errors, zero warnings)
- `pytest`: **1969 passed**, 84 failed (pre-existing `test_workload_coverage.py` failures — sprint-numbered test directory checks, scheduled for Sprint 6)
- No new test failures introduced

## Files Changed

| File | Action |
|------|--------|
| `docs-site/docs/user-guide/ai-assistant.md` | Rewritten |
| `docs-site/docs/user-guide/exporting.md` | Rewritten |
| `docs-site/docs/user-guide/calculation-reference.md` | Rewritten |
| `docs-site/docs/user-guide/faq.md` | Created |
| `docs-site/sidebars.ts` | Modified (added FAQ) |
| `harness/contracts/sprint-4.md` | Created |
| `harness/state.json` | Updated |

## Known Limitations

- Conversation examples in AI Assistant guide use placeholder cost values (`~$X,XXX`) since actual costs depend on the specific configuration at runtime
- The FAQ "Can the AI assistant modify my existing workloads?" answer reflects current behavior — if this changes, the FAQ needs updating
- Worked examples use AWS us-east-1 Premium pricing. Other cloud/region/tier combinations will produce different numbers.
