# Sprint 1 Handoff: Screenshot Audit & Test Data Setup

## What Was Built

### Audit Report
- **`harness/audit/screenshot-audit-report.md`** — Comprehensive audit of all 39 screenshots (8 core + 31 guides). Visually inspected every image for customer name violations, number overflow, and stale UI. Found 2 critical violations (real customer name "Maya Merchant") and 1 quality issue (cluttered debug data).

### Capture Checklist
- **`harness/audit/capture-checklist.md`** — Step-by-step checklist for re-capturing the 3 core screenshots that need updating (home-page.png, estimates-list.png, all-workloads-overview.png), including pre-capture data sanitization steps.

### Validation Test Suite (183 tests)
- **`tests/docs_media/test_image_references.py`** — Validates all 61 markdown `![...](/img/...)` references resolve to existing files, checks alt text is present and non-empty, verifies core screenshots are referenced, checks file sizes.
- **`tests/docs_media/test_screenshot_audit.py`** — Validates audit report exists and covers all 39 screenshots, verifies all core and guide screenshot files exist, checks directory structure (gifs/, video/).
- **`tests/docs_media/test_docs_build.py`** — Validates docs site builds (`npm run build`) without errors, checks package.json has build script.
- **`tests/docs_media/conftest.py`** — Shared fixtures and path constants.

### Directory Structure
- **`docs-site/static/img/gifs/`** — Created for Sprint 4 workflow GIFs
- **`docs-site/static/video/`** — Created for Sprint 5 tutorial video

## Audit Summary

| Category | Total | Violations | Quality Issues | Clean |
|----------|-------|------------|----------------|-------|
| Core screenshots | 8 | 2 | 1 | 5 |
| Guide screenshots | 31 | 0 | 0 | 31 |

### Screenshots Requiring Re-capture
1. **`home-page.png`** — CRITICAL: Shows "Maya Merchant Commerci..." (real customer name)
2. **`estimates-list.png`** — CRITICAL: Shows "Maya Merchant Commerci..." (real customer name)
3. **`all-workloads-overview.png`** — WARN: Cluttered with 25+ debug/test workload entries

### Alt Text Review
All 61 image references across 38 doc files have descriptive, non-empty alt text. No updates needed.

## How to Test

1. Run the validation tests:
   ```bash
   cd "/Users/steven.tan/Desktop/Ent 1 - Q4 FY 2026 Team Project/lakemeter_app"
   pytest tests/docs_media/ -v
   ```
2. Build the docs site:
   ```bash
   cd docs-site && npm run build
   ```

## Test Results

- `pytest tests/docs_media/`: **183 passed**, 1 warning (custom mark)
- `npm run build`: exit code **0**, zero errors

## Known Limitations

- The 3 screenshots flagged for re-capture (home-page, estimates-list, all-workloads-overview) still contain the violations. Re-capture requires browser access to the live app via Chrome DevTools MCP, which is handled by the Visual QA Agent.
- The `login-page.png` shows "GCP fe-vending-machine Account (FEVM)" — this is an internal workspace name, not a customer name. Flagged as acceptable but could be refreshed for cleanliness.

## Files Changed

- `harness/contracts/sprint-1.md` (updated for media overhaul spec)
- `harness/audit/screenshot-audit-report.md` (new)
- `harness/audit/capture-checklist.md` (new)
- `tests/docs_media/__init__.py` (new)
- `tests/docs_media/conftest.py` (new)
- `tests/docs_media/test_image_references.py` (new)
- `tests/docs_media/test_screenshot_audit.py` (new)
- `tests/docs_media/test_docs_build.py` (new)
- `docs-site/static/img/gifs/` (new directory)
- `docs-site/static/video/` (new directory)
- `harness/handoffs/sprint-1-handoff.md` (updated)
- `harness/state.json` (updated)
