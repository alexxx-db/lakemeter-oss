# Sprint 3 Handoff: DLT/SDP (Spark Declarative Pipelines) — AI Assistant Tests

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
- **6 DLT Core Edition tests** (separate module-scoped fixture):
  - workload_type == "DLT"
  - dlt_edition contains "CORE" for basic ETL pipeline
  - workload_name non-empty
  - proposal_id present
  - classic compute has node types and num_workers >= 1
  - photon_enabled set for classic compute
- **6 DLT Advanced Edition tests** (separate module-scoped fixture):
  - workload_type == "DLT"
  - dlt_edition contains "ADVANCED" for full monitoring
  - workload_name non-empty
  - proposal_id present
  - serverless_enabled explicitly set
  - scheduling fields present

### Design Decisions
- 3-message sequences per variant (primary → detailed follow-up → explicit proposal request) to handle AI clarification behavior
- Prompts use both "DLT" and "SDP" terminology to match how the AI agent is instructed (internal enum = DLT, user-facing = SDP)
- Edition assertions use case-insensitive `.upper()` + `in` check for robustness

## How to Test

```bash
cd "/Users/steven.tan/Desktop/Ent 1 - Q4 FY 2026 Team Project/lakemeter_app"
source .venv/bin/activate
python -m pytest tests/ai_assistant/sprint_3/ -v
```

Requires: Databricks CLI profile `lakemeter` configured with workspace access.

## Test Results

- **52 tests passed** (18 S1 + 13 S2 + 21 S3), 0 failed, 0 errors
- Runtime: ~449s (7m 29s) for full AI assistant suite; ~173s for Sprint 3 only
- Module-scoped fixtures: 3 AI calls for Sprint 3 (PRO, CORE, ADVANCED)
- Each variant uses 3 messages; AI proposes within the sequence on all 3 variants

## Known Limitations

- Tests are non-deterministic: AI may produce different field values across runs
- DLT Core was requested as classic compute but AI may sometimes choose serverless — tests adapt (classic-specific checks are conditional on `serverless_enabled=False`)
- DLT Advanced was requested as serverless but assertions don't strictly require it
- Each variant makes its own AI call (~30-60s each)

## Files Changed

- `tests/ai_assistant/sprint_3/__init__.py` — NEW (module init)
- `tests/ai_assistant/sprint_3/conftest.py` — NEW (sprint-specific fixtures placeholder)
- `tests/ai_assistant/sprint_3/test_dlt_proposal.py` — NEW (21 tests)
- `harness/contracts/sprint-3.md` — Updated for AI assistant tests
- `harness/handoffs/sprint-3-handoff.md` — This file
