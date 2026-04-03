# Sprint 5 Handoff: Admin Guide Accuracy & Update (Iteration 4)

## What Was Built

### Iteration 1–3 (prior)
All 8 admin guide pages audited and rewritten against current codebase. 20+ missing frontend convenience endpoints added to api-reference.md. Three accuracy gaps fixed (ENVIRONMENT description, CORS defaults, backend/root app.yaml difference).

### Iteration 4 (this iteration)
Deep cross-verification of all 8 admin guide pages against every referenced source file. Two accuracy gaps found and fixed:

1. **architecture.md — Export module count**:
   - Was: "Export Engine (Excel/XLSX, 11 modules)"
   - Now: "Export Engine (Excel/XLSX, 10 modules)" — correctly counts source files excluding `__init__.py`

2. **Swagger/Docusaurus disambiguation (4 pages)**:
   - In production, FastAPI's Swagger docs at `/docs` are disabled, but the Docusaurus documentation site is served at `/docs/` as static files. Four pages (`configuration.md`, `deployment.md`, `api-reference.md`, `troubleshooting.md`) now explicitly say "Swagger API docs" and note the Docusaurus site is unaffected.

### Full Verification Results (All 8 Pages)
- **deployment.md** — Verified against `deploy.sh` (4 steps), both `app.yaml` files. Steps, env vars, and auth flow accurate.
- **configuration.md** — Verified against `config.py` Settings class. All env vars, CORS defaults, SP credential flow, DB connection pool params accurate.
- **installer.md** — Verified against `install_lakemeter.py`. All 5 CLI flags, 7 config params, 9-step flow match.
- **architecture.md** — Verified against actual file tree. 9 routers, 11 models, 10 export modules, frontend structure all accurate.
- **permissions.md** — Verified against `token_manager.py` and `database.py`. 3 permission layers, token lifecycle (30-min refresh, 15-min pool recycle), test list accurate.
- **api-reference.md** — All endpoints verified against route files and `main.py`. 9 routers + main.py endpoints + debug endpoints all documented.
- **troubleshooting.md** — Debug endpoints verified in `main.py`. CORS defaults consistent with configuration.md. Swagger/Docusaurus distinction clarified.
- **database.md** — Verified against `models/estimate.py`, `models/line_item.py`, `models/user.py`. All columns match including `discount_config` (added by installer ALTER TABLE).

## How to Test

- **Docs build**: `cd docs-site && npm run build` (verified — builds cleanly, zero errors)
- **Navigate**: Open any admin guide page and cross-reference against the source file it documents
- **Configuration check**: Compare env var table against `backend/app/config.py` Settings class

## Test Results

- `npm run build`: SUCCESS (zero errors, zero warnings)
- `pytest`: 1969 passed, 84 failed (all pre-existing in `test_workload_coverage.py`), 2 skipped (148s)
- No new test failures introduced

## Known Limitations

- Screenshots are not included (documentation content sprint)
- JWT settings (`jwt_secret_key`, `jwt_algorithm`, `access_token_expire_minutes`) exist in `config.py` but are unused — correctly omitted from docs
- Some GPU DBU rates in `main.py` hardcoded endpoints have minor rounding differences vs. the `/reference/` path variants (e.g., Azure A100 80GB 1x: 78.5 vs 78.6 DBU/hr)

## Files Changed

- `docs-site/docs/admin-guide/architecture.md` — Fixed export module count (11 → 10)
- `docs-site/docs/admin-guide/configuration.md` — Clarified Swagger vs Docusaurus docs disambiguation
- `docs-site/docs/admin-guide/deployment.md` — Clarified Swagger vs Docusaurus docs disambiguation
- `docs-site/docs/admin-guide/api-reference.md` — Clarified Swagger vs Docusaurus docs disambiguation
- `docs-site/docs/admin-guide/troubleshooting.md` — Clarified Swagger vs Docusaurus docs disambiguation
- `harness/handoffs/sprint-5-handoff.md` — Updated
- `harness/state.json` — Updated
