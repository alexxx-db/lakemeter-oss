# Sprint 9 Contract: LAKEBASE Workload Proposal Tests

## Feature
Validate that the AI assistant correctly proposes LAKEBASE workloads for PostgreSQL database requests, with proper CU sizing, HA configuration, storage, and read replica fields.

## Acceptance Criteria

### Positive: HA Production Database (AC-1 to AC-10)
- AC-1: `workload_type` == `LAKEBASE`
- AC-2: `lakebase_ha_enabled` is `true` (or `lakebase_num_read_replicas` > 0 or `lakebase_ha_nodes` > 1)
- AC-3: `lakebase_storage_gb` is populated and > 0
- AC-4: `lakebase_storage_gb` approximately 500 (range 50-5000)
- AC-5: `lakebase_cu` is populated and >= 1 (production HA = at least 1 CU)
- AC-6: `lakebase_cu` approximately 4 (range 1-32)
- AC-7: `workload_name` is non-empty and descriptive (>= 3 chars)
- AC-8: `reason` is populated (>= 10 chars)
- AC-9: `notes` is populated
- AC-10: `proposal_id` is present

### Positive: Small Dev/Test Instance (AC-11 to AC-17)
- AC-11: `workload_type` == `LAKEBASE`
- AC-12: `lakebase_storage_gb` approximately 10 (range 1-100)
- AC-13: `lakebase_cu` is small (range 0.25-4)
- AC-14: HA is NOT enabled (or `lakebase_ha_enabled` == false / `lakebase_num_read_replicas` == 0)
- AC-15: `workload_name` non-empty
- AC-16: `reason` populated
- AC-17: `proposal_id` present

### Negative Discrimination: ETL Jobs (AC-18 to AC-19)
- AC-18: ETL batch pipeline request should NOT be LAKEBASE
- AC-19: Should be JOBS type instead

### Negative Discrimination: SQL Analytics (AC-20 to AC-21)
- AC-20: SQL analytics/BI request should NOT be LAKEBASE
- AC-21: Should be DBSQL type instead

## Test Plan
- 2 positive AI calls (HA production + small dev/test)
- 2 negative AI calls (ETL → JOBS, SQL analytics → DBSQL)
- ~30 individual test assertions across 4 test files
- Module-scoped fixtures to minimize AI calls

## Parallel Execution
- All 4 fixtures are independent — pytest can run them in any order
- Each fixture uses `send_chat_until_proposal` with 3-message escalation
