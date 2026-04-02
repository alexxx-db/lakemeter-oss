# Sprint 11 Contract: Multi-Workload ML Pipeline (AI Assistant Tests)

## Context

Sprint 10 validated multi-workload conversations for JOBS + ALL_PURPOSE + DBSQL.
Sprint 11 tests the AI assistant's ability to handle an **ML/RAG pipeline** conversation:
vector search for embeddings, Claude (proprietary FMAPI) for text generation,
and a model serving endpoint for a custom reranker — all within a single conversation.

**Prior non-AI Sprint 11 tests** (Model Serving combined validation, notes completeness,
S10 regression) remain in `tests/sprint_11/` unchanged. This contract adds AI assistant
tests in `tests/ai_assistant/sprint_11/`.

## Acceptance Criteria

### 3-Workload ML Pipeline (VECTOR_SEARCH + FMAPI_PROPRIETARY + MODEL_SERVING)
- [ ] AC-1: Conversation produces 3 proposals across turns
- [ ] AC-2: The set of workload types covers VECTOR_SEARCH, FMAPI_PROPRIETARY, MODEL_SERVING
- [ ] AC-3: Each proposal has `workload_name` (>=3 chars), `reason` (>=10 chars), `notes`, `proposal_id`
- [ ] AC-4: VECTOR_SEARCH proposal has `vector_search_endpoint_type` populated
- [ ] AC-5: FMAPI_PROPRIETARY proposal has `fmapi_provider` containing "anthropic" and `fmapi_model` containing "claude"
- [ ] AC-6: MODEL_SERVING proposal has `model_serving_type` populated
- [ ] AC-7: All 3 confirmations succeed (`success: true`, `action: confirmed`)
- [ ] AC-8: Conversation state shows >=3 confirmed workloads with matching types
- [ ] AC-9: Each proposal has a distinct `proposal_id`

### 2-Workload Variant (VECTOR_SEARCH + FMAPI_PROPRIETARY)
- [ ] AC-10: Conversation requesting only RAG embeddings + Claude produces 2 proposals
- [ ] AC-11: Types cover VECTOR_SEARCH and FMAPI_PROPRIETARY; both confirm successfully

### Negative Discrimination
- [ ] AC-12: Prompt requesting only "model serving endpoint for ML inference" produces MODEL_SERVING only

## Test Plan

- `tests/ai_assistant/sprint_11/prompts.py` — prompt constants
- `tests/ai_assistant/sprint_11/conftest.py` — module-scoped fixtures
- `tests/ai_assistant/sprint_11/test_ml_pipeline_types.py` — AC-1..AC-6
- `tests/ai_assistant/sprint_11/test_ml_pipeline_confirm.py` — AC-7..AC-9
- `tests/ai_assistant/sprint_11/test_ml_pipeline_two.py` — AC-10..AC-11
- `tests/ai_assistant/sprint_11/test_ml_pipeline_negative.py` — AC-12

## File Size Limit

All test files must be under 200 lines.
