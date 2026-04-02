# Sprint 5 Contract: MODEL_SERVING — AI Assistant Proposal Tests

## Scope

Test that the AI assistant correctly interprets natural language requests for model serving endpoints and produces valid `MODEL_SERVING` workload proposals with the right fields.

## Acceptance Criteria

### GPU Medium Variant (Primary)
- [ ] AC-1: `workload_type` == `MODEL_SERVING`
- [ ] AC-2: `model_serving_type` contains "gpu_medium" or equivalent
- [ ] AC-3: `hours_per_month` approximately matches requested value (~200)
- [ ] AC-4: `workload_name` is descriptive (length >= 3)
- [ ] AC-5: `reason` populated (length >= 10)
- [ ] AC-6: `notes` populated
- [ ] AC-7: `proposal_id` present for confirm/reject flow

### CPU Variant
- [ ] AC-8: `workload_type` == `MODEL_SERVING`
- [ ] AC-9: `model_serving_type` contains "cpu"
- [ ] AC-10: `hours_per_month` present and > 0
- [ ] AC-11: `model_serving_scale_to_zero` is boolean when present

### GPU Small Variant
- [ ] AC-12: `workload_type` == `MODEL_SERVING`
- [ ] AC-13: `model_serving_type` contains "gpu_small"
- [ ] AC-14: `hours_per_month` present and > 0

### Negative Discrimination — Non-Model-Serving Requests
- [ ] AC-15: Interactive compute request → NOT `MODEL_SERVING` (should be `ALL_PURPOSE`)
- [ ] AC-16: Batch ETL request → NOT `MODEL_SERVING` (should be `JOBS` or `DLT`)

## Prompt Variants (5 total, 5 AI calls)

1. **GPU Medium A10G** — "Deploy a model serving endpoint with GPU medium A10G, running 200 hours a month"
2. **CPU Only** — "CPU-only model serving endpoint for lightweight inference, 500 hours a month"
3. **GPU Small T4** — "GPU small T4 endpoint for real-time embeddings, 300 hours a month"
4. **Negative: Interactive** — Interactive notebook cluster request (should NOT be MODEL_SERVING)
5. **Negative: Batch ETL** — Batch ETL pipeline request (should NOT be MODEL_SERVING)

## Test Plan

- 4 test files: `test_model_serving_gpu_medium.py`, `test_model_serving_cpu.py`, `test_model_serving_gpu_small.py`, `test_model_serving_negative.py`
- Module-scoped fixtures (one AI call per variant, shared across tests)
- Multi-message escalation pattern (primary → followup → final) per established sprint pattern
- Each test file: 5-8 focused assertions

## Production Readiness Items This Sprint
- N/A (testing-only run)
