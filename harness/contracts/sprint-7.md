# Sprint 7 Contract: FMAPI_DATABRICKS — AI Assistant Proposal Tests

## Scope

Test that the Lakemeter AI assistant correctly interprets natural-language requests for
**Databricks-hosted Foundation Model API** usage and proposes valid `FMAPI_DATABRICKS`
workload configurations via the `propose_workload` tool.

## Prompt Variants (5 AI calls)

| # | Variant | Key Assertion |
|---|---------|--------------|
| 1 | Llama 4 Maverick, 10M input tokens | model contains "llama", rate_type="input_token", quantity~10 |
| 2 | Llama output tokens, 5M | rate_type="output_token", quantity~5 |
| 3 | BGE-Large embeddings, 20M tokens | model contains "bge" or "gte", provider="databricks"/"meta" |
| 4 | Negative: Claude API request → FMAPI_PROPRIETARY |
| 5 | Negative: GPU model serving → MODEL_SERVING |

## Acceptance Criteria

### Variant 1: Llama Input Tokens
- AC-1: `workload_type` == `FMAPI_DATABRICKS`
- AC-2: `fmapi_model` contains "llama" (case-insensitive)
- AC-3: `fmapi_rate_type` is valid token type (AI may propose input/output — both valid)
- AC-4: `fmapi_quantity` > 0, range 1-100
- AC-5: `fmapi_endpoint_type` in ["global", "regional"]
- AC-6: `workload_name` non-empty (>=3 chars)
- AC-7: `reason` populated (>=10 chars)
- AC-8: `proposal_id` present

### Variant 2: Output Tokens
- AC-9: `workload_type` == `FMAPI_DATABRICKS`
- AC-10: `fmapi_rate_type` == "output_token"
- AC-11: `fmapi_quantity` > 0, range 1-50
- AC-12: `fmapi_model` populated (non-empty)
- AC-13: `fmapi_endpoint_type` in ["global", "regional"]

### Variant 3: Embeddings Model
- AC-14: `workload_type` == `FMAPI_DATABRICKS`
- AC-15: `fmapi_model` populated — likely "bge" or "gte" or embeddings-related
- AC-16: `fmapi_quantity` > 0
- AC-17: `fmapi_provider` present

### Variant 4: Negative — Claude (FMAPI_PROPRIETARY)
- AC-18: `workload_type` != `FMAPI_DATABRICKS` (should be FMAPI_PROPRIETARY)

### Variant 5: Negative — GPU Model Serving
- AC-19: `workload_type` != `FMAPI_DATABRICKS` (should be MODEL_SERVING)

## Test Plan
- 5 module-scoped fixtures (1 AI call each, ~60s per call)
- ~25 individual test assertions across 4 test files
- Tolerant assertions (ranges, substring matches) for AI non-determinism
- 3-message escalation per variant (primary → followup → final)
