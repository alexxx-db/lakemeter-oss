# Sprint 1 Contract: Test Infrastructure + JOBS Workload

## Acceptance Criteria

- [ ] Test infrastructure: shared conftest with auth, estimate creation/cleanup, chat helpers
- [ ] Chat helper sends message to `POST /api/v1/chat` and parses response including `proposed_workload`
- [ ] Auth uses Databricks workspace token (from env var or CLI) against live app
- [ ] Test estimate created per session, cleaned up after
- [ ] JOBS test: natural language prompt produces `workload_type=JOBS` proposal
- [ ] JOBS test: `num_workers`, `runs_per_day`, `avg_runtime_minutes`, `days_per_month` present and valid
- [ ] JOBS test: `workload_name` is non-empty and descriptive
- [ ] JOBS test: `reason` and `notes` fields populated
- [ ] Confirm-workload test: confirm proposal via `POST /api/v1/chat/{id}/confirm-workload`
- [ ] Confirm-workload test: verified via `GET /api/v1/chat/{id}/state`
- [ ] Edge case: serverless vs classic defaults — AI picks reasonable config
- [ ] All tests pass with `pytest tests/ai_assistant/sprint_1/ -v`

## API Contract

- `POST /api/v1/chat` — send chat message, receive AI response with `proposed_workload`
- `POST /api/v1/chat/{id}/confirm-workload` — confirm/reject a proposed workload
- `GET /api/v1/chat/{id}/state` — get conversation state
- `POST /api/v1/estimates/` — create test estimate
- `DELETE /api/v1/estimates/{id}` — cleanup test estimate

## Test Plan

- Unit tests: N/A (testing live app)
- Integration tests: 6-8 test functions hitting live API
- Timeout: 120s per AI call (Claude can take 30-60s)
- Retry: if AI asks clarifying questions, send follow-up with specifics

## Files

- `tests/ai_assistant/__init__.py`
- `tests/ai_assistant/conftest.py` — shared fixtures (auth, estimate, chat helpers)
- `tests/ai_assistant/sprint_1/__init__.py`
- `tests/ai_assistant/sprint_1/conftest.py` — sprint-specific fixtures
- `tests/ai_assistant/sprint_1/test_jobs_proposal.py` — JOBS workload proposal tests
- `tests/ai_assistant/sprint_1/test_confirm_flow.py` — confirm/reject workload tests
