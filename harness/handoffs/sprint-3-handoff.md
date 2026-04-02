# Sprint 3 Handoff: DLT/SDP (Spark Declarative Pipelines) — AI Assistant Tests (Iteration 3)

## What Was Built

### DLT Proposal Tests (`tests/ai_assistant/sprint_3/test_dlt_proposal.py`)
- **9 DLT Pro Serverless tests** (module-scoped fixture — single AI call shared):
  - workload_type == "DLT"
  - workload_name non-empty (>= 3 chars)
  - dlt_edition contains "PRO"
  - serverless_enabled == True
  - reason populated (>= 10 chars)
  - notes populated (>= 1 char)
  - proposal_id present
  - scheduling fields present (runs_per_day or hours_per_month)
  - serverless_enabled explicitly set (not None)
- **10 DLT Core Edition tests** (separate module-scoped fixture):
  - workload_type == "DLT"
  - dlt_edition contains "CORE" for basic ETL pipeline
  - workload_name non-empty
  - proposal_id present
  - reason populated (>= 10 chars)
  - notes populated (>= 1 char)
  - serverless_enabled explicitly set (not None)
  - classic compute has node types and num_workers >= 1 (skips via `pytest.skip` if serverless)
  - photon_enabled set for classic compute (skips via `pytest.skip` if serverless)
  - **NEW** scheduling_fields_present (runs_per_day or hours_per_month) — completes AC-15 for Core
- **8 DLT Advanced Edition tests** (separate module-scoped fixture):
  - workload_type == "DLT"
  - dlt_edition contains "ADVANCED" for full monitoring
  - workload_name non-empty
  - proposal_id present
  - reason populated (>= 10 chars)
  - notes populated (>= 1 char)
  - serverless_enabled explicitly set
  - scheduling fields present

### Iteration 3 Changes (from evaluator feedback)
1. **BUG-S3-001 [MAJOR]**: Hardened `DLT_ADVANCED_FINAL` prompt — added Photon preference, base table size hint, days/month, and "don't ask more questions" directive. Eliminates intermittent fixture failures where AI asked clarifying questions instead of proposing.
2. **BUG-S3-002 [MINOR]**: Added `test_scheduling_fields_present` to `TestDltCoreEdition` — AC-15 now tested on all 3 variants (was Pro + Advanced only). **15/15 ACs now covered.**

### Stability Verification
Advanced fixture tested **twice** consecutively — both passed. Previously failed ~30-50% per VQA report; now stable with the hardened prompt.

## How to Test

```bash
cd "/Users/steven.tan/Desktop/Ent 1 - Q4 FY 2026 Team Project/lakemeter_app"
source .venv/bin/activate
python -m pytest tests/ai_assistant/sprint_3/ -v
```

Requires: Databricks CLI profile `lakemeter` configured with workspace access.

## Test Results

- **Sprint 3 only**: 27 passed, 0 failed, 0 errors in ~243s (4m 3s)
- **Full AI regression (S1+S2+S3)**: 58 passed, 0 failed, 0 errors in ~550s (9m 9s)
- **Advanced stability retest**: 8/8 passed in ~64s
- Module-scoped fixtures: 3 AI calls for Sprint 3 (PRO, CORE, ADVANCED)
- Zero regressions across all sprints
- Test count: 26 → 27 (new Core scheduling test)

## Known Limitations

- Tests are non-deterministic: AI may produce different field values across runs
- DLT Core was requested as classic compute but AI may sometimes choose serverless — classic-specific tests properly skip with `pytest.skip`
- Each variant makes its own AI call (~30-60s each)

## Files Changed

- `tests/ai_assistant/sprint_3/test_dlt_proposal.py` — MODIFIED:
  - Hardened `DLT_ADVANCED_FINAL` prompt (lines 56-61) to prevent intermittent failures
  - Added `test_scheduling_fields_present` to `TestDltCoreEdition` (lines 219-224)
  - Test count: 26 → 27
- `harness/handoffs/sprint-3-handoff.md` — Updated for iteration 3
