# Sprint 11 Handoff: Model Serving Re-validation + Sprint 10 Regression Tests

## What Was Built

Regression test suite guarding against the 4 bugs from Sprint 10 iteration 1 (BUG-S10-001 through BUG-S10-004), comprehensive Model Serving validation in the combined estimate context, and notes column completeness tests.

### New Test Files (3 files, 50 tests)

| File | Tests | Purpose |
|------|-------|---------|
| `tests/sprint_11/test_regression_s10_bugs.py` | 8 | Guards against BUG-S10-001 (invalid `gpu_medium`), BUG-S10-003 (weak FMAPI SKU), BUG-S10-004 (file size limit) |
| `tests/sprint_11/test_ms_combined_validation.py` | 34 | Model Serving in combined Excel: row exists, SKU, DBU/hr, formula, VM=0, mode; parametrized 14 GPU types × 3 clouds for rate + SKU |
| `tests/sprint_11/test_notes_completeness.py` | 8 | Storage row notes, fallback pricing notes, expected-empty notes, no `None` literals |

### Acceptance Criteria Coverage

| AC | Description | Status |
|----|------------|--------|
| AC-1 | `gpu_medium` returns 0 DBU/hr with warning | PASS |
| AC-2 | `gpu_medium_a10g_1x` returns 20.0 with no warnings | PASS |
| AC-3 | FMAPI DB SKU = `SERVERLESS_REAL_TIME_INFERENCE` (exact) | PASS |
| AC-4 | FMAPI Prop SKU = `ANTHROPIC_MODEL_SERVING` (exact) | PASS |
| AC-5 | All test files under 200 lines (sprint_10 + sprint_11) | PASS |
| AC-6 | Notes behavior documented: empty when no warnings/user input | PASS |
| AC-7 | Model Serving in combined estimate has non-zero DBU cost | PASS |
| AC-8 | Excel SKU = `SERVERLESS_REAL_TIME_INFERENCE` | PASS |
| AC-9 | Excel DBU/Hr = 20.0 for A10G 1x | PASS |
| AC-10 | Excel DBUs/Mo is a formula | PASS |
| AC-11 | No VM costs for Model Serving | PASS |
| AC-12 | All 14 GPU types across 3 clouds correct | PASS (28 parametrized tests) |
| AC-13 | Storage sub-rows have notes | PASS |
| AC-14 | Fallback pricing items documented | PASS |
| AC-15 | Empty notes documented as expected behavior | PASS |

## Test Results

- **Sprint 11 tests**: 50 passed, 0 failed (1.20s)
- **Full suite**: 1304 passed, 0 failed (5.88s)
- **Regressions**: None

## How to Test

```bash
cd "/Users/steven.tan/Desktop/Ent 1 - Q4 FY 2026 Team Project/lakemeter_app"
source .venv/bin/activate
python -m pytest tests/sprint_11/ -v
python -m pytest  # full suite
```

## Known Limitations

- Notes column behavior is documented, not changed: items without user notes or warnings have empty notes (this is correct behavior, not a bug)
- The file size limit test checks sprint_10 and sprint_11 directories only

## Files Changed

- `tests/sprint_11/__init__.py` (new)
- `tests/sprint_11/test_regression_s10_bugs.py` (new, 90 lines)
- `tests/sprint_11/test_ms_combined_validation.py` (new, 102 lines)
- `tests/sprint_11/test_notes_completeness.py` (new, 97 lines)
- `harness/contracts/sprint-11.md` (new)
- `harness/state.json` (updated)
