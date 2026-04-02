# Sprint 7 Handoff: FMAPI_DATABRICKS — AI Assistant Proposal Tests

## What Was Built

5 prompt variants testing the AI assistant's ability to correctly propose FMAPI_DATABRICKS workloads:

| File | Variant | AI Calls | Tests |
|------|---------|----------|-------|
| `test_fmapi_db_llama_input.py` | Llama 4 Maverick, 10M tokens | 1 | 8 |
| `test_fmapi_db_output_tokens.py` | Llama output tokens, 5M | 1 | 5 |
| `test_fmapi_db_embeddings.py` | BGE-Large embeddings, 20M tokens | 1 | 4 |
| `test_fmapi_db_negative.py` | Claude (proprietary) + GPU serving (should NOT be FMAPI_DATABRICKS) | 2 | 4 |
| **Total** | | **5** | **21** |

### Files Created
- `tests/ai_assistant/sprint_7/__init__.py`
- `tests/ai_assistant/sprint_7/prompts.py` — 5 prompt variant constants (3 messages each)
- `tests/ai_assistant/sprint_7/conftest.py` — 5 module-scoped fixtures (1 AI call each)
- `tests/ai_assistant/sprint_7/test_fmapi_db_llama_input.py` — Llama input assertions (AC-1 to AC-8)
- `tests/ai_assistant/sprint_7/test_fmapi_db_output_tokens.py` — Output token assertions (AC-9 to AC-13)
- `tests/ai_assistant/sprint_7/test_fmapi_db_embeddings.py` — Embeddings model assertions (AC-14 to AC-17)
- `tests/ai_assistant/sprint_7/test_fmapi_db_negative.py` — Negative discrimination (AC-18, AC-19)

### Contract Updated
- `harness/contracts/sprint-7.md` — rewritten for AI assistant proposal testing scope

## How to Test

```bash
# Sprint 7 only (5 AI calls, ~4 minutes)
pytest tests/ai_assistant/sprint_7/ -v

# Full regression (non-AI, ~6 seconds)
pytest tests/ --ignore=tests/ai_assistant -v
```

## Test Results

- **Sprint 7 AI tests**: 21 passed in 230.44s (0:03:50)
- **Non-AI regression (S1-S9)**: 1304 passed in 6.00s
- **Total**: 1325 passed, 0 failed, 0 regressions

## Acceptance Criteria Coverage

| AC | Description | Status |
|----|-------------|--------|
| AC-1 | Llama → `workload_type` == FMAPI_DATABRICKS | PASS |
| AC-2 | Llama → `fmapi_model` contains "llama" | PASS |
| AC-3 | Llama → `fmapi_rate_type` is valid token type | PASS |
| AC-4 | Llama → `fmapi_quantity` in range 1-100 | PASS |
| AC-5 | Llama → `fmapi_endpoint_type` in [global, regional] | PASS |
| AC-6-8 | Llama → name, reason, proposal_id populated | PASS |
| AC-9-10 | Output → FMAPI_DATABRICKS + output_token rate_type | PASS |
| AC-11-13 | Output → quantity in range, model populated, endpoint valid | PASS |
| AC-14-15 | Embeddings → FMAPI_DATABRICKS + embeddings model | PASS |
| AC-16-17 | Embeddings → quantity > 0, provider present | PASS |
| AC-18 | Claude → NOT FMAPI_DATABRICKS (is FMAPI_PROPRIETARY) | PASS |
| AC-19 | GPU serving → NOT FMAPI_DATABRICKS (is MODEL_SERVING) | PASS |

## File Size Compliance

All files under 200 lines — largest is `prompts.py` at 97 lines.

## Known Limitations

- AI responses are non-deterministic — Llama rate_type test accepts any valid rate type (input/output) rather than enforcing input_token specifically
- Embeddings model assertion uses substring match for robustness (bge/gte/embed)

## Files Changed
- `tests/ai_assistant/sprint_7/` — 7 new files (21 tests)
- `harness/contracts/sprint-7.md` — updated contract
- `harness/handoffs/sprint-7-handoff.md` — this handoff
