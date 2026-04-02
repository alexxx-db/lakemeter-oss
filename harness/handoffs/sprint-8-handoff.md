# Sprint 8 Handoff: FMAPI_PROPRIETARY — AI Assistant Proposal Tests (Iteration 2)

## What Was Built (Iter 1) / Fixed (Iter 2)

### Iter 1: Sprint 8 — FMAPI_PROPRIETARY tests
5 prompt variants testing the AI assistant's ability to correctly propose FMAPI_PROPRIETARY workloads for all 3 proprietary providers, plus negative discrimination:

| File | Variant | AI Calls | Tests |
|------|---------|----------|-------|
| `test_fmapi_prop_claude.py` | Claude Sonnet 4.5, 5M input tokens (Anthropic) | 1 | 9 |
| `test_fmapi_prop_openai.py` | GPT-5 mini, 20M input tokens (OpenAI) | 1 | 9 |
| `test_fmapi_prop_google.py` | Gemini 2.5 Flash, 15M input tokens (Google) | 1 | 9 |
| `test_fmapi_prop_negative.py` | Llama (-> FMAPI_DATABRICKS) + GPU serving (-> MODEL_SERVING) | 2 | 7 |
| **Total AI assistant** | | **5** | **34** |

### Iter 2: Regression fix for Sprint 5 ETL negative test
**Bug**: `tests/ai_assistant/sprint_5/test_model_serving_negative.py::TestModelServingNegativeEtl` — 2 ERRORs. The `non_serving_etl_proposal` fixture failed because the AI asked "Lakeflow Jobs (Procedural) or SDP (Declarative)?" instead of proposing a workload after 3 messages. The ETL prompts were ambiguous ("batch ETL workload" doesn't specify JOBS vs DLT).

**Fix**: Updated `tests/ai_assistant/sprint_5/prompts.py` — made all 3 ETL negative prompts explicitly specify "Lakeflow Jobs" workload type and added "I want the JOBS workload type, not DLT" to the final prompt to prevent AI clarification questions.

### Files Changed (Iter 2)
- `tests/ai_assistant/sprint_5/prompts.py` — Fixed ETL negative prompts to be explicit about JOBS type

### Files Created (Iter 1)
- `tests/ai_assistant/sprint_8/__init__.py`
- `tests/ai_assistant/sprint_8/prompts.py` — 5 prompt variants with primary/followup/final
- `tests/ai_assistant/sprint_8/conftest.py` — 5 module-scoped fixtures (1 AI call each)
- `tests/ai_assistant/sprint_8/test_fmapi_prop_claude.py` — 9 tests (AC-1 to AC-9)
- `tests/ai_assistant/sprint_8/test_fmapi_prop_openai.py` — 9 tests (AC-10 to AC-14)
- `tests/ai_assistant/sprint_8/test_fmapi_prop_google.py` — 9 tests (AC-15 to AC-19)
- `tests/ai_assistant/sprint_8/test_fmapi_prop_negative.py` — 7 tests (AC-20, AC-21)

## How to Test

```bash
# Sprint 8 AI assistant only (34 tests, ~5 minutes with AI calls)
pytest tests/ai_assistant/sprint_8/ -v

# Full non-AI regression (1340 tests, ~6 seconds)
pytest tests/ --ignore=tests/ai_assistant -v

# All AI assistant tests (206 tests, ~25 minutes)
pytest tests/ai_assistant/ -v
```

## Test Results (Iter 2)

- **Non-AI regression**: 1340 passed in 6.27s (0 failures, 0 errors)
- **Sprint 8 AI tests**: 34 collected (require live AI calls to run)
- **All AI tests**: 206 collected

## Acceptance Criteria Coverage

| AC | Description | Status |
|----|-------------|--------|
| AC-1 | Claude -> `workload_type` == FMAPI_PROPRIETARY | COVERED |
| AC-2 | Claude -> `fmapi_provider` contains anthropic | COVERED |
| AC-3 | Claude -> `fmapi_model` contains claude | COVERED |
| AC-4 | Claude -> `fmapi_rate_type` is valid token type | COVERED |
| AC-5 | Claude -> `fmapi_quantity` in range 1-100 | COVERED |
| AC-6 | Claude -> `fmapi_endpoint_type` valid | COVERED |
| AC-7 | Claude -> workload_name non-empty | COVERED |
| AC-8 | Claude -> reason populated | COVERED |
| AC-9 | Claude -> proposal_id present | COVERED |
| AC-10 | GPT -> `workload_type` == FMAPI_PROPRIETARY | COVERED |
| AC-11 | GPT -> `fmapi_provider` contains openai | COVERED |
| AC-12 | GPT -> `fmapi_model` contains gpt | COVERED |
| AC-13 | GPT -> `fmapi_quantity` > 0 | COVERED |
| AC-14 | GPT -> name, reason, proposal_id populated | COVERED |
| AC-15 | Gemini -> `workload_type` == FMAPI_PROPRIETARY | COVERED |
| AC-16 | Gemini -> `fmapi_provider` contains google | COVERED |
| AC-17 | Gemini -> `fmapi_model` contains gemini | COVERED |
| AC-18 | Gemini -> `fmapi_quantity` > 0 | COVERED |
| AC-19 | Gemini -> name, reason, proposal_id populated | COVERED |
| AC-20 | Llama -> NOT FMAPI_PROPRIETARY (FMAPI_DATABRICKS) | COVERED |
| AC-21 | GPU -> NOT FMAPI_PROPRIETARY (MODEL_SERVING) | COVERED |

## File Size Compliance

All files under 200 lines — largest is `prompts.py` at 98 lines.

## Known Limitations

- AI responses are non-deterministic — tests use tolerant assertions (substring, ranges)
- AI may propose slightly different model names (e.g., "claude-sonnet-4-5" vs "claude-4-5-sonnet")
- Quantity ranges are generous to accommodate AI's interpretation of token volume
