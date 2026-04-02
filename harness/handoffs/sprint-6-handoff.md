# Sprint 6 Handoff: VECTOR_SEARCH — AI Assistant Proposal Tests

## What Was Built

5 prompt variants × multi-message escalation testing the AI assistant's ability to correctly propose VECTOR_SEARCH workloads:

| File | Variant | AI Calls | Tests |
|------|---------|----------|-------|
| `test_vector_search_standard.py` | Standard endpoint, 50M vectors | 1 | 8 |
| `test_vector_search_storage_optimized.py` | Storage-Optimized, 200M vectors | 1 | 7 |
| `test_vector_search_small_rag.py` | Small RAG chatbot, 5M vectors | 1 | 7 |
| `test_vector_search_negative.py` | Model Serving + SQL Analytics (should NOT be VECTOR_SEARCH) | 2 | 4 |
| **Total** | | **5** | **26** |

### Files Created
- `tests/ai_assistant/sprint_6/__init__.py`
- `tests/ai_assistant/sprint_6/prompts.py` — 5 prompt variant constants (3 messages each)
- `tests/ai_assistant/sprint_6/conftest.py` — 5 module-scoped fixtures (1 AI call each)
- `tests/ai_assistant/sprint_6/test_vector_search_standard.py` — Standard endpoint assertions (AC-1 to AC-7)
- `tests/ai_assistant/sprint_6/test_vector_search_storage_optimized.py` — Storage-Optimized assertions (AC-8 to AC-11)
- `tests/ai_assistant/sprint_6/test_vector_search_small_rag.py` — Small RAG assertions (AC-12 to AC-14)
- `tests/ai_assistant/sprint_6/test_vector_search_negative.py` — Negative discrimination (AC-15, AC-16)

### Contract Updated
- `harness/contracts/sprint-6.md` — rewritten for AI assistant proposal testing scope

## How to Test

```bash
# Sprint 6 only (5 AI calls, ~5 minutes)
pytest tests/ai_assistant/sprint_6/ -v

# Full regression (non-AI, ~6 seconds)
pytest tests/ --ignore=tests/ai_assistant -v
```

## Test Results

- **Sprint 6 AI tests**: 26 passed in 299.92s (0:04:59)
- **Non-AI regression (S1-S9)**: 1304 passed in 6.00s
- **Total**: 1330 passed, 0 failed, 0 regressions

## Acceptance Criteria Coverage

| AC | Description | Status |
|----|-------------|--------|
| AC-1 | Standard → `workload_type` == VECTOR_SEARCH | PASS |
| AC-2 | Standard → `vector_search_endpoint_type` == STANDARD | PASS |
| AC-3 | Standard → `vector_capacity_millions` ~ 50 | PASS |
| AC-4-7 | Standard → name, reason, notes, proposal_id | PASS |
| AC-8-9 | Storage-Optimized → VECTOR_SEARCH + STORAGE_OPTIMIZED type | PASS |
| AC-10-11 | Storage-Optimized → capacity > 0, in range 50-500 | PASS |
| AC-12-14 | Small RAG → VECTOR_SEARCH + capacity + valid enum | PASS |
| AC-15 | Model deployment → NOT VECTOR_SEARCH (is MODEL_SERVING) | PASS |
| AC-16 | SQL analytics → NOT VECTOR_SEARCH (is DBSQL) | PASS |

## File Size Compliance

All files under 200 lines — largest is `prompts.py` at 87 lines.

## Known Limitations

- AI responses are non-deterministic — tests use tolerant ranges (e.g., capacity 5-500 instead of exact 50)
- Storage-optimized endpoint type check uses substring "STORAGE" match for robustness

## Files Changed
- `tests/ai_assistant/sprint_6/` — 6 new files (26 tests)
- `harness/contracts/sprint-6.md` — updated contract
- `harness/handoffs/sprint-6-handoff.md` — this handoff
