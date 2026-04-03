# Sprint 2 Handoff: DLT + DBSQL Parity (All Editions/Types/Sizes)

## What Was Built

### Bug Fix
- **Frontend DLT serverless photon lookup** (`costCalculation.ts:290`): Changed hardcoded `DLT_CORE_COMPUTE` to edition-specific `DLT_${dltEdition}_COMPUTE` for photon multiplier lookup in serverless mode. Currently all editions share the same multiplier (2.9 on AWS) so no visible number change, but this is a correctness fix.

### Parity Verification
- **DLT**: All 9 combinations verified (3 editions × 3 modes: Classic, Photon, Serverless)
  - Core/Pro/Advanced Classic: DBU/hr = (driver + worker × N), SKU = `DLT_{edition}_COMPUTE`
  - Core/Pro/Advanced Photon: DBU/hr × photon_mult, SKU = `DLT_{edition}_COMPUTE_(PHOTON)`
  - Core/Pro/Advanced Serverless: DBU/hr × photon_mult × mode_mult, SKU = `JOBS_SERVERLESS_COMPUTE`
  - All paths produce identical results between frontend and backend

- **DBSQL**: All 27 combinations verified (3 warehouse types × 9 sizes)
  - Classic/Pro/Serverless × 2X-Small(4) through 4X-Large(528) DBU/hr
  - Multi-cluster: DBU/hr = base × num_clusters (tested 1, 2, 3, 4, 5)
  - SKUs: `SQL_COMPUTE`, `SQL_PRO_COMPUTE`, `SERVERLESS_SQL_COMPUTE`
  - All paths produce identical results between frontend and backend

### New Tests (76 tests added)
- `tests/parity/test_parity_dlt.py`: 15 tests covering all 9 DLT combos + edge cases
- `tests/parity/test_parity_dbsql.py`: 68 tests covering all 27 DBSQL combos + multi-cluster + edge cases

## How to Test
- Start: `cd backend && uvicorn app.main:app --reload --port 8000`
- Run tests: `python -m pytest tests/ --tb=short`

## Test Results
- `pytest` exit code: 0
- Tests: **1838 passed, 0 failed** (76 new + 1762 existing)
- Duration: ~107s

## Parity Coverage (DLT)
| Config | Tests | Status |
|--------|-------|--------|
| DLT Core Classic (no photon) | 1 | PASS |
| DLT Core Photon | 1 | PASS |
| DLT Core Serverless (standard) | 1 | PASS |
| DLT Core Serverless (performance) | 1 | PASS |
| DLT Pro Classic (no photon) | 1 | PASS |
| DLT Pro Photon | 1 | PASS |
| DLT Pro Serverless (standard) | 1 | PASS |
| DLT Pro Serverless (performance) | 1 | PASS |
| DLT Advanced Classic (no photon) | 1 | PASS |
| DLT Advanced Photon | 1 | PASS |
| DLT Advanced Serverless (standard) | 1 | PASS |
| DLT Advanced Serverless (performance) | 1 | PASS |
| DLT Zero Workers | 1 | PASS |
| DLT Default Edition (None → CORE) | 1 | PASS |
| DLT Run-Based Hours | 1 | PASS |

## Parity Coverage (DBSQL)
| Config | Tests | Status |
|--------|-------|--------|
| Classic × 9 sizes (DBU/hr) | 9 | PASS |
| Classic × 9 sizes (monthly cost) | 9 | PASS |
| Pro × 9 sizes (DBU/hr) | 9 | PASS |
| Pro × 9 sizes (monthly cost) | 9 | PASS |
| Serverless × 9 sizes (DBU/hr) | 9 | PASS |
| Serverless × 9 sizes (monthly cost) | 9 | PASS |
| Multi-cluster (Classic Medium, 1/2/3/5) | 4 | PASS |
| Multi-cluster (Serverless X-Large, 1/2/4) | 3 | PASS |
| Multi-cluster (Pro Large, 1/3) | 2 | PASS |
| Default type (None → SERVERLESS) | 1 | PASS |
| Default size (None → Small) | 1 | PASS |
| Empty size ('' → Small) | 1 | PASS |
| Run-based hours | 1 | PASS |
| Null clusters (None → 1) | 1 | PASS |

## Files Changed
- `frontend/src/utils/costCalculation.ts` — DLT serverless photon lookup: `DLT_CORE_COMPUTE` → `DLT_${dltEdition}_COMPUTE`
- `tests/parity/test_parity_dlt.py` — Expanded from 3 test classes (4 tests) to 12 classes (15 tests)
- `tests/parity/test_parity_dbsql.py` — Expanded from 3 test classes (4 tests) to parametrized suite (68 tests)

## Known Limitations
- VM costs are always $0 in Excel export (intentional — frontend loads VM pricing on-demand)
- DLT photon multipliers are currently identical across all editions (2.9 on AWS, 2.5 on Azure/GCP) — the frontend fix is preemptive for if/when they diverge
