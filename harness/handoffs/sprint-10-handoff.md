# Sprint 10 Handoff: Multi-Workload — Jobs + Interactive + DBSQL

## What Was Built

AI assistant multi-workload conversation tests — 62 tests across 4 test files covering:

1. **3-workload conversation** (JOBS + ALL_PURPOSE + DBSQL): Tests that a single conversation can collect 3 distinct workload proposals, verify each has correct type and populated fields, and confirm all 3 in sequence.
2. **2-workload conversation** (JOBS + DBSQL): Tests a shorter multi-workload flow without ALL_PURPOSE.
3. **Multi-confirm flow**: Verifies all confirmations succeed, conversation state reflects all confirmed workloads, and no pending proposals remain after confirming all.
4. **Negative discrimination**: Single-workload prompt ("data science notebooks only") produces ALL_PURPOSE — not JOBS or DBSQL.

### Files Created

| File | Lines | Purpose |
|------|-------|---------|
| `tests/ai_assistant/sprint_10/__init__.py` | 0 | Package marker |
| `tests/ai_assistant/sprint_10/prompts.py` | 97 | 12 prompt constants across 3 variants |
| `tests/ai_assistant/sprint_10/conftest.py` | 133 | Module-scoped fixtures: three_workload_session, two_workload_session, negative_ds_only_proposal |
| `tests/ai_assistant/sprint_10/test_multi_three_workloads.py` | 116 | 26 tests — type checks, field assertions, workload-specific fields |
| `tests/ai_assistant/sprint_10/test_multi_two_workloads.py` | 75 | 12 tests — JOBS + DBSQL only |
| `tests/ai_assistant/sprint_10/test_multi_confirm_all.py` | 90 | 14 tests — confirm flow, conversation state |
| `tests/ai_assistant/sprint_10/test_multi_negative.py` | 56 | 8 tests — discrimination |

### Files Modified
- `harness/contracts/sprint-10.md` — updated contract for AI multi-workload tests

## How to Test

```bash
# Collect tests (no AI calls)
cd lakemeter_app
source .venv/bin/activate
pytest tests/ai_assistant/sprint_10/ --collect-only -q

# Run tests against live backend (requires Databricks CLI profile + FMAPI access)
pytest tests/ai_assistant/sprint_10/ -v --timeout=300
```

The tests use FastAPI TestClient against the local backend, which calls FMAPI (Claude Sonnet 4.5) for AI proposals. Each module-scoped fixture makes 3+ AI calls, so expect ~5-10 minutes for the full suite.

## Test Results

- **Sprint 10 AI tests**: 62 collected, require live FMAPI (not run in build phase)
- **Full non-AI regression**: 1387/1387 passed (6.79s)
- **Syntax check**: All 7 files pass

## Known Limitations

- AI responses are non-deterministic — the AI may propose workloads in a different order or ask clarifying questions. The prompt sequences include followup messages to handle this.
- The 3-workload test fixture is expensive (~6+ AI calls with retries). Module-scoped fixtures share results across tests in the same file.
- The conversation state endpoint (`/state`) response shape may vary — tests check for `confirmed_workloads` and `proposed_workloads` keys defensively.
