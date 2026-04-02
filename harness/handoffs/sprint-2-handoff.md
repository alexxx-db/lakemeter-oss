# Sprint 2 Handoff: ALL_PURPOSE (Interactive Compute) — AI Assistant Tests

## What Was Built

### ALL_PURPOSE Proposal Tests (`tests/ai_assistant/sprint_2/test_allpurpose_proposal.py`)
- **11 basic ALL_PURPOSE tests** (module-scoped fixture — single AI call shared):
  - workload_type == "ALL_PURPOSE"
  - workload_name non-empty (>= 3 chars)
  - num_workers present and >= 1
  - hours_per_month present and in reasonable range (50-750)
  - driver_node_type populated
  - worker_node_type populated
  - pricing tier field(s) present
  - reason populated (>= 10 chars)
  - notes populated (>= 1 char)
  - proposal_id present
  - serverless_enabled explicitly set
- **2 edge case tests** (separate module-scoped fixture):
  - Interactive notebook prompt maps to ALL_PURPOSE (not JOBS)
  - hours_per_month present and > 0 for interactive use case
- **Flakiness fix (iteration 1)**: Added 3rd follow-up message (`INTERACTIVE_AMBIGUOUS_FINAL`) to edge case prompts — the AI sometimes asks clarifying questions instead of proposing on the 2nd message. More explicit prompts with specific instance types and parameters reduce non-determinism.

## How to Test

```bash
cd "/Users/steven.tan/Desktop/Ent 1 - Q4 FY 2026 Team Project/lakemeter_app"
source .venv/bin/activate
python -m pytest tests/ai_assistant/sprint_2/ -v
```

Requires: Databricks CLI profile `lakemeter` configured with workspace access.

## Test Results

- **31 tests passed** (18 Sprint 1 + 13 Sprint 2), 0 failed, 0 errors
- Runtime: ~287s (4m 47s) for full suite; ~120s for Sprint 2 only
- Module-scoped fixtures minimize AI calls (2 for Sprint 2 proposals = 2 total AI calls)
- Edge case may use up to 3 AI calls if AI asks clarifying questions

## Architecture Decision

Follows Sprint 1 pattern: FastAPI TestClient with local backend for FMAPI access. Module-scoped fixtures share expensive AI calls across test methods in the same class.

## Known Limitations

- Tests are non-deterministic: AI may produce different field values across runs
- hours_per_month assertion uses wide range (50-750) to account for AI interpretation variability
- Each edge case variant makes its own AI call (~30-60s each)
- Edge case prompts use 3 messages to handle AI clarification requests; may occasionally still need retry if AI is unusually terse

## Files Changed

- `tests/ai_assistant/sprint_2/__init__.py` — NEW (module init)
- `tests/ai_assistant/sprint_2/conftest.py` — NEW (sprint-specific fixtures placeholder)
- `tests/ai_assistant/sprint_2/test_allpurpose_proposal.py` — NEW (13 tests)
- `harness/contracts/sprint-2.md` — Updated for AI assistant tests
- `harness/handoffs/sprint-2-handoff.md` — This file
