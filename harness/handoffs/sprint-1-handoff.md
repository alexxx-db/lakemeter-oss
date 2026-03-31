# Sprint 1 Handoff: Jobs (Classic + Serverless) — Iteration 3

## What Was Built / Fixed

This iteration addressed the two remaining evaluator-cited issues that the Build Agent can control:

### 1. BUG-S1-15: Deprecation Warnings Eliminated (Production Readiness)
All 11 deprecation warnings that fired during test collection have been fixed:

- **Pydantic V2**: Replaced `class Config: from_attributes = True` with `model_config = ConfigDict(from_attributes=True)` in 9 schema classes across 6 files:
  - `backend/app/schemas/estimate.py` (4 classes: LineItemSummary, EstimateResponse, EstimateListResponse, EstimateWithLineItemsResponse)
  - `backend/app/schemas/line_item.py` (1 class: LineItemResponse)
  - `backend/app/schemas/user.py` (1 class: UserResponse)
  - `backend/app/schemas/workload_type.py` (1 class: WorkloadTypeResponse)
  - `backend/app/schemas/sharing.py` (1 class: ShareResponse)
  - `backend/app/schemas/vm_pricing.py` (1 class: VMPricingResponse)
- **Pydantic Settings**: Fixed `backend/app/config.py` Settings class — replaced `class Config` with `model_config = ConfigDict(env_file=".env", case_sensitive=False, extra="ignore")`
- **SQLAlchemy**: Changed `backend/app/database.py` import from `sqlalchemy.ext.declarative` to `sqlalchemy.orm`

### 2. Regression Tests for BUG-S1-15
Added `TestBugS1_15_DeprecationWarningsFixed` class (3 tests) to `tests/regression/test_sprint_1_bugs.py`:
- `test_no_pydantic_class_config_in_schemas` — scans all schema files for deprecated pattern
- `test_no_deprecated_declarative_base_import` — verifies database.py uses correct import
- `test_config_py_uses_configdict` — verifies config.py uses modern pattern

### Prior Fixes Still Verified (All Passing)
- **BUG-S1-5**: Serverless photon 2x always applied (3 regression tests)
- **BUG-S1-6**: Lakebase DBU formula cu × nodes (3 regression tests)
- **BUG-S1-12**: num_workers defaults to 0, not 1 (3 regression tests)
- **BUG-S1-13**: Hours fallback returns 0, not 11 (3 regression tests)
- **BUG-S1-1**: Shared fixture extracted to conftest.py (3 regression tests)
- **BUG-S1-3**: Integration test exists with endpoint tests (2 regression tests)

## Test Files

| File | Tests | Purpose |
|------|-------|---------|
| `tests/sprint_1/test_jobs_calculations.py` | 19 | Frontend/backend calc logic, all 4 configs |
| `tests/sprint_1/test_jobs_export.py` | 18 | Backend export helpers (_get_sku_type, etc.) |
| `tests/sprint_1/test_jobs_excel_export.py` | 20 | Excel formula verification with openpyxl |
| `tests/sprint_1/test_jobs_vm_and_notes.py` | 20 | VM costs, notes, NaN/$0 regression |
| `tests/sprint_1/test_jobs_discrepancies.py` | 7 | Frontend vs backend alignment verification |
| `tests/sprint_1/test_jobs_export_integration.py` | 10 | Real endpoint integration with TestClient |
| `tests/regression/test_sprint_1_bugs.py` | 20 | Regression tests for all 7 fixed bugs |

**Total Sprint 1 scope: 128 sprint tests + 20 regression tests = 148 tests**

## How to Test

```bash
# Run Sprint 1 tests only
cd "/Users/steven.tan/Desktop/Ent 1 - Q4 FY 2026 Team Project/lakemeter_app"
python -m pytest tests/sprint_1/ tests/regression/test_sprint_1_bugs.py -v

# Run full suite (all sprints)
python -m pytest tests/ -v

# Verify zero deprecation warnings
python -m pytest tests/ -W error::DeprecationWarning
```

**Live app**: https://lakemeter-e2e-v2-335310294452632.aws.databricksapps.com

## Test Results

```
Sprint 1 + Regression: 148 passed, 0 failed, 0 warnings (1.93s)
Full suite (all sprints): 572 passed, 0 failed, 0 warnings (5.53s)
```

**Zero warnings** — all 11 deprecation warnings from prior iterations eliminated.

## Known Limitations

- **No Visual QA**: No live browser testing performed — Visual QA Agent responsibility
- **File size violations**: Pre-existing (ai_agent.py: 3,822 lines, Calculator.tsx: 4,106 lines) — out of scope for testing-only run
- **VM pricing**: Tests use hardcoded $0.20/$0.10 VM rates from export logic, not dynamic lookups

## Files Changed

| File | Change |
|------|--------|
| `backend/app/database.py` | SQLAlchemy import: `ext.declarative` → `orm` |
| `backend/app/config.py` | `class Config` → `model_config = ConfigDict(...)` |
| `backend/app/schemas/estimate.py` | 4× `class Config` → `model_config = ConfigDict(...)` |
| `backend/app/schemas/line_item.py` | `class Config` → `model_config = ConfigDict(...)` |
| `backend/app/schemas/user.py` | `class Config` → `model_config = ConfigDict(...)` |
| `backend/app/schemas/workload_type.py` | `class Config` → `model_config = ConfigDict(...)` |
| `backend/app/schemas/sharing.py` | `class Config` → `model_config = ConfigDict(...)` |
| `backend/app/schemas/vm_pricing.py` | `class Config` → `model_config = ConfigDict(...)` |
| `tests/regression/test_sprint_1_bugs.py` | Added 3 regression tests for BUG-S1-15 |
