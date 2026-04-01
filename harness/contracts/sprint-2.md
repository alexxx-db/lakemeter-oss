# Sprint 2 Contract: ALL_PURPOSE (Interactive Compute) — AI Assistant Tests

## Acceptance Criteria

- [ ] AC-1: Interactive compute prompt produces `workload_type=ALL_PURPOSE`
- [ ] AC-2: `num_workers` present and >= 1 (user asked for 8 workers)
- [ ] AC-3: `hours_per_month` present and reasonable for "8 hours a day" (120-200 range)
- [ ] AC-4: `driver_node_type` populated (non-empty string)
- [ ] AC-5: `worker_node_type` populated (non-empty string)
- [ ] AC-6: Pricing tier fields present (`driver_pricing_tier` and/or `worker_pricing_tier`)
- [ ] AC-7: `workload_name` is descriptive (>= 3 chars)
- [ ] AC-8: `reason` populated (>= 10 chars)
- [ ] AC-9: `notes` populated (>= 1 char)
- [ ] AC-10: `proposal_id` present for confirm/reject flow
- [ ] AC-11: Edge case — AI distinguishes ALL_PURPOSE from JOBS for interactive use case
- [ ] AC-12: All tests pass with `pytest tests/ai_assistant/sprint_2/ -v`

## API Contract

Same as Sprint 1 — `POST /api/v1/chat` with `mode=estimate`.

## Test Plan

- Module-scoped fixture: single AI call for interactive cluster proposal, shared across test class
- 12+ test functions covering all acceptance criteria
- Edge case test uses separate conversation to verify type distinction
- Timeout: 120s per AI call
- Follow-up messages if AI asks clarifying questions

## Files

- `tests/ai_assistant/sprint_2/__init__.py`
- `tests/ai_assistant/sprint_2/conftest.py`
- `tests/ai_assistant/sprint_2/test_allpurpose_proposal.py`

## Production Readiness Items This Sprint
- N/A (testing-only run)
