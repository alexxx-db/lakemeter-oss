# Sprint 5 Handoff: MODEL_SERVING — AI Assistant Proposal Tests

## What Was Built

5 prompt variants × multi-message escalation testing the AI assistant's ability to correctly propose MODEL_SERVING workloads:

| File | Variant | AI Calls | Tests |
|------|---------|----------|-------|
| `test_model_serving_gpu_medium.py` | GPU Medium (A10G), 200 hrs/mo | 1 | 8 |
| `test_model_serving_cpu.py` | CPU only, 500 hrs/mo, scale-to-zero | 1 | 8 |
| `test_model_serving_gpu_small.py` | GPU Small (T4), 300 hrs/mo | 1 | 8 |
| `test_model_serving_negative.py` | Interactive + Batch ETL (should NOT be MODEL_SERVING) | 2 | 4 |
| **Total** | | **5** | **28** |

### Files Created
- `tests/ai_assistant/sprint_5/__init__.py`
- `tests/ai_assistant/sprint_5/prompts.py` — 5 prompt variant constants (3 messages each)
- `tests/ai_assistant/sprint_5/conftest.py` — 5 module-scoped fixtures (1 AI call each)
- `tests/ai_assistant/sprint_5/test_model_serving_gpu_medium.py` — GPU medium assertions (AC-1 to AC-7)
- `tests/ai_assistant/sprint_5/test_model_serving_cpu.py` — CPU assertions (AC-8 to AC-11)
- `tests/ai_assistant/sprint_5/test_model_serving_gpu_small.py` — GPU small assertions (AC-12 to AC-14)
- `tests/ai_assistant/sprint_5/test_model_serving_negative.py` — Negative discrimination (AC-15, AC-16)

### Contract Updated
- `harness/contracts/sprint-5.md` — rewritten for AI assistant proposal testing scope

## How to Test

```bash
# Sprint 5 only (5 AI calls, ~4 minutes)
pytest tests/ai_assistant/sprint_5/ -v

# Full regression (non-AI, ~6 seconds)
pytest tests/ --ignore=tests/ai_assistant -v
```

## Test Results

- **Sprint 5 AI tests**: 28 passed in 249.64s (0:04:09)
- **Non-AI regression (S1-S9)**: 1304 passed in 5.96s
- **Total**: 1332 passed, 0 failed, 0 regressions

## Acceptance Criteria Coverage

| AC | Description | Status |
|----|-------------|--------|
| AC-1 | GPU Medium → `workload_type` == MODEL_SERVING | PASS |
| AC-2 | GPU Medium → `model_serving_type` contains gpu_medium | PASS |
| AC-3 | GPU Medium → `hours_per_month` ~ 200 | PASS |
| AC-4-7 | GPU Medium → name, reason, notes, proposal_id | PASS |
| AC-8-9 | CPU → MODEL_SERVING + cpu type | PASS |
| AC-10 | CPU → hours_per_month > 0 | PASS |
| AC-11 | CPU → scale_to_zero is boolean when present | PASS |
| AC-12-14 | GPU Small → MODEL_SERVING + gpu_small + hours | PASS |
| AC-15 | Interactive compute → NOT MODEL_SERVING | PASS |
| AC-16 | Batch ETL → NOT MODEL_SERVING | PASS |

## File Size Compliance

All files under 200 lines — largest is `prompts.py` at 87 lines.

## Known Limitations

- AI responses are non-deterministic — tests use tolerant assertions (e.g., hours range 100-744 instead of exact 200)
- `model_serving_scale_to_zero` test is conditional (checked only when field is present, since AI may not always include it)

## Files Changed
- `tests/ai_assistant/sprint_5/` — 6 new files (28 tests)
- `harness/contracts/sprint-5.md` — updated contract
- `harness/handoffs/sprint-5-handoff.md` — this handoff
