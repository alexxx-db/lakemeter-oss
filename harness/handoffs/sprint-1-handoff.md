# Sprint 1 Handoff: Test Infrastructure + JOBS Workload

## What Was Built

### Test Infrastructure (`tests/ai_assistant/conftest.py`)
- FastAPI TestClient wrapping the local backend with Lakebase + FMAPI access
- Auto-configures env vars for Databricks CLI auth, SP credentials via secrets scope
- Session-scoped test estimate (created once, cleaned up after)
- Chat helper utilities:
  - `send_chat_message()` — sends non-streaming chat, retries on 500 with 30s backoff
  - `extract_proposal()` — extracts `proposed_workload` from response or tool_results
  - `send_chat_until_proposal()` — sends multiple messages until a proposal is returned
  - `confirm_proposal()` / `reject_proposal()` — confirm/reject via REST API
  - `get_conversation_state()` — check conversation state

### JOBS Workload Tests (`tests/ai_assistant/sprint_1/test_jobs_proposal.py`)
- **11 classic JOBS tests** (module-scoped fixture — single AI call shared):
  - workload_type == "JOBS"
  - workload_name non-empty (>= 3 chars)
  - runs_per_day, avg_runtime_minutes, days_per_month present and > 0
  - num_workers present and >= 1
  - reason populated (>= 10 chars)
  - proposal_id present
  - serverless_enabled explicitly set
  - photon_enabled set for classic compute
  - node types populated for classic compute
- **3 serverless JOBS tests** (separate module-scoped fixture):
  - workload_type == "JOBS"
  - serverless_enabled == True
  - scheduling fields (runs_per_day, avg_runtime_minutes) present

### Confirm Workflow Tests (`tests/ai_assistant/sprint_1/test_confirm_flow.py`)
- **3 tests** (each creates its own conversation):
  - Confirm proposal returns success with workload_config
  - Confirmed proposal is removed from pending list in conversation state
  - Reject proposal returns success with "rejected" action

## How to Test

```bash
cd /Users/steven.tan/Desktop/Ent\ 1\ -\ Q4\ FY\ 2026\ Team\ Project/lakemeter_app
python -m pytest tests/ai_assistant/sprint_1/ -v
```

Requires: Databricks CLI profile `lakemeter` configured with workspace access.

## Test Results

- **17 tests passed**, 0 failed
- Runtime: ~220s (3m 40s) — AI calls take 30-60s each
- Module-scoped fixtures minimize AI calls (2 for proposals, 3 for confirm flow = 5 total)

## Architecture Decision: TestClient vs Live App

Initially attempted to test against the live Databricks App at `https://lakemeter-e2e-v2-335310294452632.aws.databricksapps.com`. The Databricks Apps proxy re-scopes OAuth tokens, removing `model-serving` scope needed for FMAPI (Claude API). Switched to FastAPI TestClient which uses the backend's CLI token fallback — this token has `all-apis` scope including `model-serving`.

## Known Limitations

- Tests are non-deterministic: AI may ask different clarifying questions across runs. Follow-up messages mitigate this but 3 messages may not always be enough.
- Each confirm flow test makes its own AI call (~30-60s each) since they need independent conversations.
- Rate limiting: Claude FMAPI has QPH limits. Running full suite repeatedly may hit rate limits.

## Files Changed

- `tests/ai_assistant/__init__.py` (new)
- `tests/ai_assistant/conftest.py` (new — shared test infrastructure)
- `tests/ai_assistant/sprint_1/__init__.py` (new)
- `tests/ai_assistant/sprint_1/conftest.py` (new — sprint-specific fixtures)
- `tests/ai_assistant/sprint_1/test_jobs_proposal.py` (new — 14 JOBS tests)
- `tests/ai_assistant/sprint_1/test_confirm_flow.py` (new — 3 confirm flow tests)
- `harness/contracts/sprint-1.md` (updated — AI assistant test contract)
- `harness/state.json` (updated)
