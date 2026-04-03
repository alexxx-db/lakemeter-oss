# Sprint 4 Handoff: AI Assistant, Export, & Calculation Reference (Iteration 4)

## What Was Built (Iter 1-3) + Fixed (Iteration 4)

### Iteration 4: Comprehensive Source Code Verification + Accuracy Fixes

Performed exhaustive verification of all 4 Sprint 4 pages against backend source code, pricing data files, and frontend calculation logic. Used parallel subagent exploration to verify every claim.

### Fix 1: FAQ — Photon Multiplier Description

**Problem**: FAQ troubleshooting section stated "Photon — Doubles the DBU rate." This is only accurate for All-Purpose compute. Jobs and DLT use different multipliers.

**Correction**: Updated to "Increases the DBU rate by a multiplier that depends on the workload type and cloud provider (2.9x for Jobs/DLT on AWS, 2.5x on Azure/GCP, 2.0x for All-Purpose)."

**Verified against**: `backend/static/pricing/dbu-multipliers.json`:
- `aws:JOBS_COMPUTE:photon` = 2.9
- `aws:DLT_CORE_COMPUTE:photon` = 2.9
- `aws:ALL_PURPOSE_COMPUTE:photon` = 2.0
- `azure:JOBS_COMPUTE:photon` = 2.5
- `gcp:JOBS_COMPUTE:photon` = 2.5

### Fix 2: Export Guide — Legend Section Colors

**Problem**: The Legend description listed Orange as one of the legend items. The actual Excel export's Legend section (`excel_sections.py:write_legend`) does NOT include Orange — it only documents Blue, Cyan, Pink, Green, Purple, and a Serverless note.

**Correction**: Updated legend description to match actual Excel output. Added clarifying note that Orange headers are used for workload identity columns but aren't listed in the Legend section.

**Verified against**: `backend/app/routes/export/excel_sections.py` lines 82-96.

## Verification Summary (Iteration 4)

All claims across all 4 Sprint 4 pages verified against source code:

| Page | Claims Verified | Issues Found | Status |
|------|----------------|--------------|--------|
| AI Assistant | 5 tools (names match), 2 modes, trim_threshold=25, max_recent=15, no edit capability | 0 | ✓ All accurate |
| Export | Sheet name, filename format, 30 columns, bulk export, color coding, frozen panes, multi-row workloads, assumptions section, legend section | 1 (legend colors) | ✓ Fixed |
| Calculation Reference | All 4 worked examples, all formula references, all SKU names, all pricing rates | 0 | ✓ All accurate |
| FAQ | 10 Q&A answers, workload type table, tier descriptions, troubleshooting tips | 1 (Photon description) | ✓ Fixed |

### Pricing Data Verified

| Claim | Source File | Value | Match |
|-------|-----------|-------|-------|
| JOBS_COMPUTE_(PHOTON) AWS us-east-1 Premium | dbu-rates.json | $0.15/DBU | ✓ |
| JOBS_SERVERLESS_COMPUTE AWS us-east-1 Premium | dbu-rates.json | $0.35/DBU | ✓ |
| SERVERLESS_SQL_COMPUTE AWS us-east-1 Premium | dbu-rates.json | $0.70/DBU | ✓ |
| SERVERLESS_REAL_TIME_INFERENCE AWS us-east-1 Premium | dbu-rates.json | $0.07/DBU | ✓ |
| DATABASE_SERVERLESS_COMPUTE AWS us-east-1 Premium | dbu-rates.json | $0.40/DBU | ✓ |
| Jobs Photon multiplier AWS | dbu-multipliers.json | 2.9x | ✓ |
| All-Purpose Photon multiplier | dbu-multipliers.json | 2.0x | ✓ |
| i3.xlarge DBU rate | instance-dbu-rates.json | 1.0 DBU/hr | ✓ |
| i3.xlarge VM price | vm_pricing.py | $0.312/hr | ✓ |
| Llama 3.1 8B input rate | fmapi-databricks-rates.json | 2.143 DBU/1M | ✓ |
| Llama 3.1 8B output rate | fmapi-databricks-rates.json | 6.429 DBU/1M | ✓ |
| DBSQL Medium size DBU | dbsql-rates.json | 24 DBU/hr | ✓ |
| Vector Search Standard divisor | vector-search-rates.json | 2,000,000 | ✓ |
| Vector Search Storage Opt divisor | vector-search-rates.json | 64,000,000 | ✓ |
| Lakebase DSU pricing | excel_item_helpers.py | 15 DSU/GB × $0.023/DSU | ✓ |
| Lakebase max storage | ai_agent.py | 8,192 GB | ✓ |
| AI trim_threshold | ai_agent.py:1272 | 25 | ✓ |
| AI max_recent_messages | ai_agent.py:1272 | 15 | ✓ |

### Calculation Logic Verified

| Formula | Source | Match |
|---------|--------|-------|
| Jobs Classic DBU/hr = (driver + worker×n) × photon | costCalculation.ts | ✓ |
| Jobs Serverless DBU/hr = (driver + worker×n) × photon × mode | costCalculation.ts | ✓ |
| DBSQL DBU/hr = size_map[size] × clusters | costCalculation.ts | ✓ |
| Lakebase DBU/hr = CU × nodes | costCalculation.ts | ✓ |
| Vector Search units = ceil(capacity/divisor) | costCalculation.ts | ✓ |
| DLT Serverless uses JOBS_SERVERLESS_COMPUTE SKU | costCalculation.ts:171 | ✓ |

## Files Changed (Iteration 4)

| File | Change |
|------|--------|
| `docs-site/docs/user-guide/faq.md` | Fixed Photon multiplier description from "Doubles" to accurate variable multiplier |
| `docs-site/docs/user-guide/exporting.md` | Fixed legend section to match actual Excel output colors |

## How to Test

1. Start docs dev server: `cd docs-site && npm run start`
2. Check pages:
   - **FAQ** (`/user-guide/faq`): Troubleshooting section, item #3 about Photon now shows accurate multiplier values
   - **Exporting** (`/user-guide/exporting`): Legend section now matches actual Excel output
   - **Calculation Reference** (`/user-guide/calculation-reference`): All 4 worked examples unchanged (verified accurate)
   - **AI Assistant** (`/user-guide/ai-assistant`): Unchanged (verified accurate)

## Test Results

- `npm run build`: **PASS** (zero errors, zero warnings)
- `pytest`: **1969 passed**, 84 failed (pre-existing `test_workload_coverage.py` failures — sprint-numbered test directory checks, scheduled for Sprint 6)
- No new test failures introduced

## Known Limitations

- Conversation examples in AI Assistant guide use placeholder cost values (`~$X,XXX`) since actual costs depend on specific configuration at runtime
- Worked examples use AWS us-east-1 Premium pricing. Other combinations produce different numbers.
- The 84 pre-existing test failures are all in `test_workload_coverage.py` checking for sprint-numbered test directories — scheduled for Sprint 6 cleanup
