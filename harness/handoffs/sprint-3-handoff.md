# Sprint 3 Handoff: DLT/SDP (Spark Declarative Pipelines) — AI Assistant Tests (Iteration 4)

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
  - scheduling_fields_present (runs_per_day or hours_per_month)
- **8 DLT Advanced Edition tests** (separate module-scoped fixture):
  - workload_type == "DLT"
  - dlt_edition contains "ADVANCED" for full monitoring
  - workload_name non-empty
  - proposal_id present
  - reason populated (>= 10 chars)
  - notes populated (>= 1 char)
  - serverless_enabled explicitly set
  - scheduling fields present

### Iteration 4 Changes (from VQA report — BUG-S3-003)

**BUG-S3-003 [CRITICAL]: Databricks FMAPI tool_use/tool_result mismatch**

Root cause: The Databricks FMAPI endpoint (Claude Opus 4.5) cannot convert OpenAI-format assistant messages that contain BOTH `content` and `tool_calls` fields to Anthropic format. When the AI responds with text AND a tool call in the same turn, the follow-up API call fails with `messages.1: tool_use ids were found without tool_result blocks`.

**Two fixes applied:**

1. **`backend/app/services/ai_client.py` (primary fix):** When formatting assistant messages with `tool_calls`, always omit the `content` field. The OpenAI spec allows tool_calls without content, and this prevents the FMAPI conversion bug.

2. **`backend/app/services/ai_agent.py` (defense-in-depth):** The non-streaming `chat()` method now uses simplified history (text-only) after tool execution, matching the existing streaming `chat_stream()` approach. Tool_calls and tool_result structures are used only for the immediate follow-up API call and then replaced with a text summary in conversation history.

### Prior Iteration Fixes (still in place)
- **BUG-S3-001** (iter 3): Hardened `DLT_ADVANCED_FINAL` prompt — added Photon, base table size, "don't ask more questions"
- **BUG-S3-002** (iter 3): Added `test_scheduling_fields_present` to `TestDltCoreEdition` — 15/15 ACs

## How to Test

```bash
cd "/Users/steven.tan/Desktop/Ent 1 - Q4 FY 2026 Team Project/lakemeter_app"
source .venv/bin/activate
python -m pytest tests/ai_assistant/sprint_3/ -v
```

Requires: Databricks CLI profile `lakemeter` configured with workspace access.

## Test Results

- **Sprint 3 only**: 27 passed, 0 failed, 0 errors in ~140s (2m 20s)
- **Full AI regression (S1+S2+S3)**: 58 passed, 0 failed, 0 errors in ~386s (6m 25s)
- Module-scoped fixtures: 3 AI calls for Sprint 3 (PRO, CORE, ADVANCED)
- Zero regressions across all sprints
- All 3 DLT variants stable (Pro, Core, Advanced)

## Known Limitations

- Tests are non-deterministic: AI may produce different field values across runs
- DLT Core was requested as classic compute but AI may sometimes choose serverless — classic-specific tests properly skip with `pytest.skip`
- Each variant makes its own AI call (~30-60s each)

## Files Changed

- `backend/app/services/ai_client.py` — MODIFIED:
  - When formatting assistant messages with tool_calls, always omit content field to prevent FMAPI conversion bug (BUG-S3-003)
- `backend/app/services/ai_agent.py` — MODIFIED:
  - Non-streaming `chat()` now uses simplified history after tool execution (text-only, matching streaming path)
- `harness/handoffs/sprint-3-handoff.md` — Updated for iteration 4
