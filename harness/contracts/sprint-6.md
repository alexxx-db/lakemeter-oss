# Sprint 6 Contract: VECTOR_SEARCH — AI Assistant Proposal Tests

## Scope

Test that the AI assistant correctly interprets natural language requests for vector search endpoints and produces valid `VECTOR_SEARCH` workload proposals with the right fields (`vector_search_endpoint_type`, `vector_capacity_millions`).

## Acceptance Criteria

### Standard Endpoint Variant (Primary)
- [ ] AC-1: `workload_type` == `VECTOR_SEARCH`
- [ ] AC-2: `vector_search_endpoint_type` is `STANDARD` (or contains "standard")
- [ ] AC-3: `vector_capacity_millions` approximately matches requested (~50)
- [ ] AC-4: `workload_name` is descriptive (length >= 3)
- [ ] AC-5: `reason` populated (length >= 10)
- [ ] AC-6: `notes` populated
- [ ] AC-7: `proposal_id` present for confirm/reject flow

### Storage-Optimized Variant
- [ ] AC-8: `workload_type` == `VECTOR_SEARCH`
- [ ] AC-9: `vector_search_endpoint_type` is `STORAGE_OPTIMIZED` (or contains "storage")
- [ ] AC-10: `vector_capacity_millions` present and > 0 (requested ~200M)
- [ ] AC-11: `vector_capacity_millions` in reasonable range for 200M request (50-500)

### Small RAG Variant
- [ ] AC-12: `workload_type` == `VECTOR_SEARCH`
- [ ] AC-13: `vector_capacity_millions` present and > 0
- [ ] AC-14: `vector_search_endpoint_type` populated with valid enum

### Negative Discrimination — Non-Vector-Search Requests
- [ ] AC-15: Model deployment request → NOT `VECTOR_SEARCH` (should be `MODEL_SERVING`)
- [ ] AC-16: SQL analytics request → NOT `VECTOR_SEARCH` (should be `DBSQL`)

## Prompt Variants (5 total, 5 AI calls)

1. **Standard 50M** — "Set up vector search for RAG with 50 million embeddings"
2. **Storage-Optimized 200M** — "I need storage-optimized vector search for 200M vectors"
3. **Small RAG 5M** — "Small vector search for RAG chatbot with 5M document embeddings"
4. **Negative: Model Deployment** — ML model deployment request (should NOT be VECTOR_SEARCH)
5. **Negative: SQL Analytics** — SQL warehouse for BI (should NOT be VECTOR_SEARCH)

## Test Plan

- 4 test files in `tests/ai_assistant/sprint_6/`
- Module-scoped fixtures (one AI call per variant, shared across tests)
- Multi-message escalation pattern (primary → followup → final)
- Each test file: 4-8 focused assertions

## Files to Create
- tests/ai_assistant/sprint_6/__init__.py
- tests/ai_assistant/sprint_6/prompts.py
- tests/ai_assistant/sprint_6/conftest.py
- tests/ai_assistant/sprint_6/test_vector_search_standard.py
- tests/ai_assistant/sprint_6/test_vector_search_storage_optimized.py
- tests/ai_assistant/sprint_6/test_vector_search_small_rag.py
- tests/ai_assistant/sprint_6/test_vector_search_negative.py

## Production Readiness Items This Sprint
- N/A (testing-only run)
