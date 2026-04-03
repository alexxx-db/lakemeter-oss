# Sprint 4 Handoff: AI Assistant, Export, & Calculation Reference (Iteration 2)

## What Was Built (Iteration 1) + Fixed (Iteration 2)

### AI Assistant Guide (`docs-site/docs/user-guide/ai-assistant.md`)
- Complete rewrite with 4 concrete conversation examples:
  1. Creating a single workload from natural language
  2. Generating a complete multi-workload estimate
  3. Optimizing an existing estimate
  4. Getting a GenAI architecture recommendation (RAG chatbot)
- Documents all 5 agent tools in a reference table — **verified against `backend/app/services/ai_agent.py`**:
  - `propose_workload`, `ask_clarifying_questions`, `get_estimate_summary`, `analyze_estimate`, `propose_genai_architecture`
- Explains both Home Mode (Q&A) and Estimate Mode (full tool use)
- Documents the Confirm/Edit/Cancel workflow for AI-proposed workloads
- Notes on conversation history limits and streaming

### Export Guide (`docs-site/docs/user-guide/exporting.md`)
- Complete rewrite documenting the full Excel export structure:
  - 6 sections: Header, Workloads Table, Multi-Row Workloads, Cost Summary, Legend, Assumptions
  - 30-column layout — **verified against `backend/app/routes/export/excel_columns.py` (NUM_COLS = 30)**
  - Color-coded header explanation — **verified against `excel_formats.py`**
  - Formatting: frozen panes, formulas, currency, landscape — **verified against `excel_builder.py`**
- File naming: `Databricks_Estimate_{name}_{YYYYMMDD}.xlsx` — **verified against `routes.py`**
- Multi-row workloads for Lakebase and Vector Search — **verified against `excel_item_helpers.py`**

### Calculation Reference (`docs-site/docs/user-guide/calculation-reference.md`)
- 4 fully worked examples with real pricing data
- **Iteration 2 fix**: Corrected Lakebase CU range from "0.5 to 112" to "1, 2, 4, or 8" — **verified against `WorkloadForm.tsx:1867-1870`**
- Updated Lakebase nodes description to "1, 2 (primary + 1 read replica), or 3 (primary + 2 read replicas)"
- All DBSQL warehouse size DBU mappings verified against `calculations.py:102-104`
- Vector Search divisor/rate values verified against `vector-search-rates.json`
- Serverless multiplier logic verified against `calculations.py:85-92`

### FAQ Page (`docs-site/docs/user-guide/faq.md`) — NEW
- 13 questions across 5 categories
- All internal links cross-checked
- Added to sidebar under Features category

## How to Test

1. Start docs dev server: `cd docs-site && npm run start`
2. Navigate to each page:
   - **AI Assistant** (`/user-guide/ai-assistant`): 4 conversation examples, tool table
   - **Exporting** (`/user-guide/exporting`): Column group table, multi-row explanation, use cases
   - **Calculation Reference** (`/user-guide/calculation-reference`): 4 worked examples, Lakebase section now shows correct CU sizes (1, 2, 4, 8)
   - **FAQ** (`/user-guide/faq`): 13 Q&A items, all internal links resolve
3. Sidebar: FAQ appears under Features after Calculation Reference

## Test Results

- `npm run build`: **PASS** (zero errors, zero warnings)
- `pytest`: **1969 passed**, 84 failed (pre-existing `test_workload_coverage.py` failures — sprint-numbered test directory checks, scheduled for Sprint 6)
- No new test failures introduced

## Iteration 2 Changes

| File | Change |
|------|--------|
| `docs-site/docs/user-guide/calculation-reference.md` | Fixed Lakebase CU range: "0.5 to 112" → "1, 2, 4, or 8"; updated nodes description |

## Source Code Verification Summary

All doc claims verified against source code in iteration 2:

| Claim | Verified Against | Status |
|-------|-----------------|--------|
| 5 AI assistant tools | `backend/app/services/ai_agent.py` TOOLS array | ✓ |
| 30 export columns | `excel_columns.py` NUM_COLS = 30 | ✓ |
| Color coding (6 colors) | `excel_formats.py` header formats | ✓ |
| File naming convention | `export/routes.py` line 38 | ✓ |
| Frozen panes, landscape | `excel_builder.py` lines 46-49 | ✓ |
| Formula-based cells | `excel_row_writer.py` | ✓ |
| DBSQL size→DBU mapping | `calculations.py` lines 102-104 | ✓ |
| Vector Search rates | `vector-search-rates.json` | ✓ |
| Lakebase CU sizes | `WorkloadForm.tsx` lines 1867-1870 | ✓ (FIXED) |
| Lakebase storage: 15 DSU × $0.023 | `ai_agent.py` line 1118 | ✓ |
| Lakebase max storage: 8192 GB | `WorkloadForm.tsx` line 1890 | ✓ |
| Serverless multiplier logic | `calculations.py` lines 85-92 | ✓ |
| Photon multiplier = 2.0 | `calculations.py` line 86 | ✓ |
| Fallback DBU = 0.5 | `calculations.py` lines 56-57 | ✓ |

## Known Limitations

- Conversation examples in AI Assistant guide use placeholder cost values (`~$X,XXX`) since actual costs depend on specific configuration at runtime
- Worked examples use AWS us-east-1 Premium pricing. Other combinations produce different numbers.
- The 84 pre-existing test failures are all in `test_workload_coverage.py` checking for sprint-numbered test directories — scheduled for Sprint 6 cleanup
