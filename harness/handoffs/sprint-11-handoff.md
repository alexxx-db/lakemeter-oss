# Sprint 11 Handoff: Multi-Workload ML Pipeline (AI Assistant Tests)

## What Was Built

AI assistant end-to-end tests for a multi-workload ML/RAG pipeline conversation:
VECTOR_SEARCH + FMAPI_PROPRIETARY + MODEL_SERVING. Follows the same patterns
as Sprint 10 (JOBS + ALL_PURPOSE + DBSQL) but targets AI/ML workload types.

### AI Test Files (6 files, 57 tests)

| File | Lines | Tests | Purpose |
|------|-------|-------|---------|
| `tests/ai_assistant/sprint_11/prompts.py` | 119 | — | Prompt constants for 3-wl, 2-wl, negative scenarios |
| `tests/ai_assistant/sprint_11/conftest.py` | 147 | — | Module-scoped fixtures: ml_pipeline_session, two_ml_session, negative_ms_only_proposal |
| `tests/ai_assistant/sprint_11/test_ml_pipeline_types.py` | 138 | 24 | AC-1..AC-6: type checks, common fields, type-specific fields |
| `tests/ai_assistant/sprint_11/test_ml_pipeline_confirm.py` | 90 | 12 | AC-7..AC-9: confirm flow, conversation state, distinct IDs |
| `tests/ai_assistant/sprint_11/test_ml_pipeline_two.py` | 81 | 14 | AC-10..AC-11: 2-workload VS + FMAPI variant |
| `tests/ai_assistant/sprint_11/test_ml_pipeline_negative.py` | 52 | 7 | AC-12: model serving only (negative discrimination) |

### Prior Non-AI Tests (unchanged)

| File | Tests | Purpose |
|------|-------|---------|
| `tests/sprint_11/test_regression_s10_bugs.py` | 8 | S10 regression guards |
| `tests/sprint_11/test_ms_combined_validation.py` | 34 | Model Serving in combined Excel |
| `tests/sprint_11/test_notes_completeness.py` | 8 | Notes column completeness |

## Acceptance Criteria Coverage

| AC | Description | Test File |
|----|------------|-----------|
| AC-1 | 3 proposals collected | test_ml_pipeline_types.py |
| AC-2 | Types cover VS, FMAPI_PROP, MS | test_ml_pipeline_types.py |
| AC-3 | Common fields (name, reason, notes, proposal_id) | test_ml_pipeline_types.py |
| AC-4 | VS has endpoint_type populated | test_ml_pipeline_types.py |
| AC-5 | FMAPI_PROP has anthropic provider + claude model | test_ml_pipeline_types.py |
| AC-6 | MS has model_serving_type populated | test_ml_pipeline_types.py |
| AC-7 | All 3 confirmations succeed | test_ml_pipeline_confirm.py |
| AC-8 | State shows >= 3 confirmed with correct types | test_ml_pipeline_confirm.py |
| AC-9 | Distinct proposal_ids | test_ml_pipeline_confirm.py |
| AC-10 | 2-workload: VS + FMAPI_PROP | test_ml_pipeline_two.py |
| AC-11 | Both confirmations succeed | test_ml_pipeline_two.py |
| AC-12 | Negative: MS only, no VS/FMAPI | test_ml_pipeline_negative.py |

## Test Results

- **Default pytest (non-AI)**: 1409 passed, 0 failed (9.58s) — no regressions
- **Sprint 11 AI tests collected**: 57 tests (excluded from default run; require FMAPI)
- **All files under 200 lines**: verified

## How to Test

```bash
cd "/Users/steven.tan/Desktop/Ent 1 - Q4 FY 2026 Team Project/lakemeter_app"
source .venv/bin/activate

# Default pytest (excludes AI tests)
pytest -v

# Sprint 11 AI tests (explicit, requires FMAPI access)
pytest tests/ai_assistant/sprint_11/ --no-header --timeout=300

# Sprint 11 non-AI tests
pytest tests/sprint_11/ -v
```

## Known Limitations

- AI tests are non-deterministic (LLM responses vary) — auto-skip if FMAPI unreachable
- The AI may propose workloads in different order than prompted; tests check the SET of types
- If the AI uses `propose_genai_architecture` (bundle tool) instead of individual proposals, `extract_proposal` may need extension

## Files Created

- `tests/ai_assistant/sprint_11/__init__.py`
- `tests/ai_assistant/sprint_11/prompts.py` (119 lines)
- `tests/ai_assistant/sprint_11/conftest.py` (147 lines)
- `tests/ai_assistant/sprint_11/test_ml_pipeline_types.py` (138 lines)
- `tests/ai_assistant/sprint_11/test_ml_pipeline_confirm.py` (90 lines)
- `tests/ai_assistant/sprint_11/test_ml_pipeline_two.py` (81 lines)
- `tests/ai_assistant/sprint_11/test_ml_pipeline_negative.py` (52 lines)

## Files Modified

- `harness/contracts/sprint-11.md` (updated with AI test contract)
- `harness/state.json` (updated)
