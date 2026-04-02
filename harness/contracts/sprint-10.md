# Sprint 10 Contract: Multi-Workload — Jobs + Interactive + DBSQL

## Feature

Test that the AI assistant can handle a multi-workload conversation where a single user describes a data platform needing daily ETL jobs, interactive notebooks, and a SQL warehouse. The AI should propose at least 3 workloads (JOBS, ALL_PURPOSE, DBSQL) across conversation turns, and each should be confirmable.

## Acceptance Criteria

- [ ] AC-1: Single conversation prompt requesting "ETL jobs + interactive notebooks + SQL warehouse" produces at least one proposal
- [ ] AC-2: Across conversation turns, AI proposes workloads covering JOBS, ALL_PURPOSE, and DBSQL types
- [ ] AC-3: Each proposed workload has correct `workload_type` field matching the expected type
- [ ] AC-4: Each proposed workload has populated `workload_name`, `reason`, and `notes` fields
- [ ] AC-5: Each proposed workload has a valid `proposal_id` for confirm/reject flow
- [ ] AC-6: All 3 proposals can be confirmed successfully (confirm returns `success=True`)
- [ ] AC-7: After confirming all 3, conversation state shows all confirmed workloads
- [ ] AC-8: Negative test — a prompt requesting only "data science notebooks" should NOT produce JOBS or DBSQL
- [ ] AC-9: Two-workload variant — "ETL pipeline + SQL analytics" produces JOBS + DBSQL (no ALL_PURPOSE)
- [ ] AC-10: Multi-workload conversation continues correctly after first proposal is confirmed

## Test Plan

### `tests/ai_assistant/sprint_10/prompts.py`
- Multi-workload prompt sequences (primary + followup + final for each variant)
- Negative prompts for discrimination testing

### `tests/ai_assistant/sprint_10/conftest.py`
- Module-scoped fixtures for multi-workload conversations
- Helper to collect multiple proposals from a single conversation

### `tests/ai_assistant/sprint_10/test_multi_three_workloads.py`
- Full 3-workload conversation: JOBS + ALL_PURPOSE + DBSQL
- Verify each proposal type, fields, and confirm flow

### `tests/ai_assistant/sprint_10/test_multi_two_workloads.py`
- 2-workload variant: JOBS + DBSQL
- Verify correct types without ALL_PURPOSE

### `tests/ai_assistant/sprint_10/test_multi_confirm_all.py`
- Confirm all proposals in sequence
- Verify conversation state after all confirmations

### `tests/ai_assistant/sprint_10/test_multi_negative.py`
- Single-workload prompt should not produce unrelated types
