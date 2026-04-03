# Sprint 2 Contract: DLT + DBSQL Parity (All Editions/Types/Sizes)

## Acceptance Criteria

### DLT Parity
- [ ] DLT Core Classic (no photon): backend DBU/hr, SKU, $/DBU, monthly cost match frontend
- [ ] DLT Core Classic (photon): backend uses correct photon multiplier from `DLT_CORE_COMPUTE`
- [ ] DLT Pro Classic (no photon): SKU = `DLT_PRO_COMPUTE`, pricing matches
- [ ] DLT Pro Classic (photon): SKU = `DLT_PRO_COMPUTE_(PHOTON)`, photon mult from `DLT_PRO_COMPUTE`
- [ ] DLT Advanced Classic (no photon): SKU = `DLT_ADVANCED_COMPUTE`
- [ ] DLT Advanced Classic (photon): SKU = `DLT_ADVANCED_COMPUTE_(PHOTON)`, photon mult from `DLT_ADVANCED_COMPUTE`
- [ ] DLT Core Serverless (standard mode): SKU = `JOBS_SERVERLESS_COMPUTE`, photon applied, mode_mult = 1
- [ ] DLT Core Serverless (performance mode): mode_mult = 2
- [ ] DLT Pro Serverless (standard): photon mult from `DLT_PRO_COMPUTE` (not `DLT_CORE_COMPUTE`)
- [ ] DLT Advanced Serverless (performance): photon mult from `DLT_ADVANCED_COMPUTE`
- [ ] Frontend DLT serverless photon lookup fixed to use edition-specific SKU (not always `DLT_CORE_COMPUTE`)

### DBSQL Parity
- [ ] All 9 warehouse sizes produce correct DBU/hr: 2X-Small(4), X-Small(6), Small(12), Medium(24), Large(40), X-Large(80), 2X-Large(144), 3X-Large(272), 4X-Large(528)
- [ ] DBSQL Classic: SKU = `SQL_COMPUTE` for all sizes
- [ ] DBSQL Pro: SKU = `SQL_PRO_COMPUTE` for all sizes
- [ ] DBSQL Serverless: SKU = `SERVERLESS_SQL_COMPUTE` for all sizes
- [ ] Multi-cluster: DBU/hr = base_dbu × num_clusters (tested with 1, 2, 3 clusters)
- [ ] Hours/month calculations match (run-based and direct)
- [ ] Monthly cost = DBU/hr × hours × $/DBU matches between frontend and backend

### Regression
- [ ] All 1762 existing tests still pass
- [ ] No changes to JOBS or ALL_PURPOSE calculation paths

## Known Issue to Fix
- **DLT serverless photon lookup** (from Sprint 1 finding): Frontend `costCalculation.ts:290` always uses `DLT_CORE_COMPUTE` for photon lookup regardless of edition. Backend correctly uses `DLT_{edition}_COMPUTE`. Currently produces same result (all editions have 2.9 multiplier on AWS) but is a correctness bug. Fix frontend to use `DLT_${dltEdition}_COMPUTE`.

## Test Plan
- Parity tests: Extend `tests/parity/test_parity_dlt.py` with all 9 DLT combinations (3 editions × 3 modes)
- Parity tests: Extend `tests/parity/test_parity_dbsql.py` with all 27 DBSQL combinations (3 types × 9 sizes)
- Regression: Full `pytest tests/` must pass
