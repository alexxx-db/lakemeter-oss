# Sprint 3 Contract: DLT/SDP (Spark Declarative Pipelines) — AI Assistant Tests

## Acceptance Criteria

### DLT Pro Serverless Proposal
- [ ] AC-1: AI proposes `workload_type=DLT` when asked for a CDC pipeline with Pro edition
- [ ] AC-2: `dlt_edition` contains "PRO" (case-insensitive)
- [ ] AC-3: `serverless_enabled=true` when serverless is requested
- [ ] AC-4: `workload_name` is non-empty (>= 3 chars)
- [ ] AC-5: `reason` populated (>= 10 chars)
- [ ] AC-6: `notes` populated (>= 1 char)
- [ ] AC-7: `proposal_id` present for confirm/reject flow

### DLT Core Edition Variant
- [ ] AC-8: "basic DLT pipeline" prompt → `dlt_edition` contains "CORE"
- [ ] AC-9: `workload_type=DLT` (not JOBS or other type)

### DLT Advanced Edition Variant
- [ ] AC-10: "Advanced DLT pipeline with full monitoring" → `dlt_edition` contains "ADVANCED"
- [ ] AC-11: `workload_type=DLT`

### Common Fields for All DLT Proposals
- [ ] AC-12: `serverless_enabled` is explicitly set (not None)
- [ ] AC-13: For classic compute, `photon_enabled` field is set
- [ ] AC-14: For classic compute, node type(s) are populated
- [ ] AC-15: Scheduling fields present (runs_per_day/hours_per_month)

## Test Plan

- **Module-scoped fixtures**: 3 AI calls total (PRO serverless, CORE basic, ADVANCED)
- **3-message sequences**: Primary prompt → detailed follow-up → explicit proposal request
- **Pattern**: Follow Sprint 1/2 conventions — TestDltProposalBasic class for shared tests, separate classes for edition variants

## Files to Create

- `tests/ai_assistant/sprint_3/__init__.py`
- `tests/ai_assistant/sprint_3/conftest.py`
- `tests/ai_assistant/sprint_3/test_dlt_proposal.py`
