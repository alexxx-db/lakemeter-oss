# Sprint 8 Contract: FMAPI_PROPRIETARY — AI Assistant Proposal Tests

## Feature
Test that the AI assistant correctly proposes FMAPI_PROPRIETARY workloads for proprietary model providers (Anthropic, OpenAI, Google) with correct fields, and discriminates against non-proprietary requests.

## Acceptance Criteria

### Positive: Claude (Anthropic)
- [ ] AC-1: `workload_type` == `FMAPI_PROPRIETARY`
- [ ] AC-2: `fmapi_provider` contains `anthropic`
- [ ] AC-3: `fmapi_model` contains `claude`
- [ ] AC-4: `fmapi_rate_type` is a valid token type
- [ ] AC-5: `fmapi_quantity` > 0 and in reasonable range (1-100)
- [ ] AC-6: `fmapi_endpoint_type` is valid (global, in_geo)
- [ ] AC-7: `workload_name` non-empty (>= 3 chars)
- [ ] AC-8: `reason` populated (>= 10 chars)
- [ ] AC-9: `proposal_id` present

### Positive: GPT (OpenAI)
- [ ] AC-10: `workload_type` == `FMAPI_PROPRIETARY`
- [ ] AC-11: `fmapi_provider` contains `openai`
- [ ] AC-12: `fmapi_model` contains `gpt`
- [ ] AC-13: `fmapi_quantity` > 0
- [ ] AC-14: `workload_name`, `reason`, `proposal_id` populated

### Positive: Gemini (Google)
- [ ] AC-15: `workload_type` == `FMAPI_PROPRIETARY`
- [ ] AC-16: `fmapi_provider` contains `google`
- [ ] AC-17: `fmapi_model` contains `gemini`
- [ ] AC-18: `fmapi_quantity` > 0
- [ ] AC-19: `workload_name`, `reason`, `proposal_id` populated

### Negative Discrimination
- [ ] AC-20: Llama request → NOT FMAPI_PROPRIETARY (should be FMAPI_DATABRICKS)
- [ ] AC-21: GPU model serving request → NOT FMAPI_PROPRIETARY (should be MODEL_SERVING)

## Test Plan
- 3 positive variants: Claude input tokens, GPT input tokens, Gemini input tokens
- 2 negative variants: Llama (FMAPI_DATABRICKS), GPU serving (MODEL_SERVING)
- Module-scoped fixtures to minimize AI calls (1 call per variant = 5 total)
- Tolerant assertions (substring match, ranges) for non-deterministic AI

## Files to Create
- `tests/ai_assistant/sprint_8/__init__.py`
- `tests/ai_assistant/sprint_8/prompts.py`
- `tests/ai_assistant/sprint_8/conftest.py`
- `tests/ai_assistant/sprint_8/test_fmapi_prop_claude.py`
- `tests/ai_assistant/sprint_8/test_fmapi_prop_openai.py`
- `tests/ai_assistant/sprint_8/test_fmapi_prop_google.py`
- `tests/ai_assistant/sprint_8/test_fmapi_prop_negative.py`
