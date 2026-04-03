# Sprint 3 Handoff: VECTOR_SEARCH + MODEL_SERVING + LAKEBASE Parity

## What Was Built

Comprehensive parity tests for the three remaining serverless workload types, verifying that backend Excel export calculations exactly match frontend cost formulas.

### Vector Search (18 tests)
- **Standard mode**: 1M, 2M (boundary), 3M (ceiling), 5M, 10M, 50M vectors
- **Storage-optimized mode**: 1M, 64M (boundary), 100M, 200M vectors
- **Storage sub-rows**: within free tier, exceeds free tier, zero storage, storage-optimized free tier, large billable
- **Total cost**: compute DBU cost + storage cost combined verification

### Model Serving (17 tests)
- **All 7 AWS GPU types**: cpu (1.0), gpu_small_t4 (10.48), gpu_medium_a10g_1x (20.0), gpu_medium_a10g_4x (112.0), gpu_medium_a10g_8x (290.8), gpu_xlarge_a100_40gb_8x (538.4), gpu_xlarge_a100_80gb_8x (628.0)
- **Case-insensitive**: GPU_SMALL_T4 → gpu_small_t4
- **Run-based usage**: 10 runs/day × 30 min × 22 days
- **Parametrized cost matrix**: all 7 GPU types verified in one parametrized test

### Lakebase (23 tests)
- **CU sizes**: 1, 2, 4, 8, 16 CU
- **HA nodes**: 1, 2, 3 nodes with parametrized CU×nodes combinations
- **Storage DSU pricing**: 100, 500, 1000, 8192 GB (max)
- **Total cost**: compute + storage combined
- **Run-based usage**: 8 runs/day × 60 min × 22 days
- **Edge cases**: CU=0, storage=None, zero storage

### Frontend calc helper
- Added `fe_vector_search_storage_cost()` to `tests/parity/frontend_calc.py`

## How to Test

```bash
# Run Sprint 3 parity tests only
pytest tests/parity/test_parity_vector_search.py tests/parity/test_parity_model_serving.py tests/parity/test_parity_lakebase.py -v

# Run all parity tests
pytest tests/parity/ -v

# Run full suite
pytest tests/ -v
```

## Test Results

- `pytest` exit code: 0
- Tests: **1884 passed** (was 1838 before Sprint 3 → +46 new tests)
- Sprint 3 specific: **58 new tests** (18 VS + 17 MS + 23 LB)
- No mismatches found — backend and frontend calculations are aligned

## Known Limitations

- No backend code changes were needed — the existing export code already matched the frontend formulas for these three workload types
- Tests verify against `aws` cloud/`us-east-1` region/`PREMIUM` tier; other cloud/region combos use same formulas (only rates differ)
- Storage sub-row Excel rendering is tested via calculation logic, not by generating actual Excel files (deferred to Sprint 5 formula audit)

## Files Changed

- `tests/parity/test_parity_vector_search.py` — rewritten with 18 comprehensive tests (was 4)
- `tests/parity/test_parity_model_serving.py` — rewritten with 17 comprehensive tests (was 4)
- `tests/parity/test_parity_lakebase.py` — rewritten with 23 comprehensive tests (was 4)
- `tests/parity/frontend_calc.py` — added `fe_vector_search_storage_cost()` helper
- `harness/contracts/sprint-3.md` — sprint contract
- `harness/state.json` — updated phase and action
