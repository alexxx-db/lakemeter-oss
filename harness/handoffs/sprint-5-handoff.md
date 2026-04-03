# Sprint 5 Handoff: Admin Guide Accuracy & Update

## What Was Built

All 8 admin guide pages were audited against the current codebase and rewritten for accuracy:

### deployment.md
- Updated `app.yaml` snippet to match actual root-level config (includes `DB_PORT`, `DB_SSLMODE`, SP key names)
- Documented `deploy.sh` as the primary deployment method with its 4-step flow (frontend build, docs build, verify, deploy)
- Added build-only mode when `DATABRICKS_HOST` is not set
- Noted that `/docs` and `/redoc` are disabled in production
- Documented both root `app.yaml` (full-repo) and `backend/app.yaml` (backend-only) variants

### configuration.md
- Rebuilt environment variable table to match `app/config.py` Settings class exactly
- Separated `valueFrom` (app resource references) from `value` (hardcoded) variables
- Added local development variables (`DATABRICKS_CONFIG_PROFILE`, `DATABASE_URL`)
- Replaced stale "secret scope keys" section with accurate SP credential flow
- Documented connection pool configuration (pool_size=5, max_overflow=10, pool_recycle=900)

### installer.md
- Verified all 9 steps against `install_lakemeter.py` source code
- Added `--dry-run` and `--non-interactive` CLI flags (were missing)
- Updated Step 2 config parameters to match `gather_config()` (7 params, not 4)
- Updated Step 4 to list all 9 application tables created
- Updated Step 5 with correct file-to-table mapping
- Added Step 9b (configure app resources) documentation

### architecture.md
- Updated backend structure to show all actual directories: `auth/` (token_manager, databricks_auth), 11 models, 9 route files, modular export (11 files)
- Updated frontend structure with all actual files: `SearchableSelect.tsx`, `EstimateDetail.tsx`, `TestCalculations.tsx`, `useTheme.ts`
- Added auth layer to system architecture diagram
- Updated data layer to show all 11 model types
- Updated AI assistant flow with `/chat/{id}/state` and `/chat/{id}/confirm-workload`

### permissions.md
- Updated token lifecycle to match `database.py` behavior: pool_recycle=900s (15 min), engine refresh every 30 min, auto-recovery on auth errors
- Cross-referenced `token_manager.py` and `database.py` for accurate refresh intervals
- Content was already largely accurate — minor updates for consistency

### api-reference.md
- Added 20+ missing endpoints discovered from source code grep:
  - `GET /api/v1/estimates/me/info`
  - `POST /api/v1/line-items/{id}/clone`
  - `GET /api/v1/chat/{id}/state`
  - `POST /api/v1/chat/{id}/confirm-workload`
  - All `/api/v1/vm-pricing/*` endpoints (6 endpoints)
  - All `/api/v1/reference/*` endpoints (12 endpoints including `/pricing-bundle/status`, `/pricing-bundle/regenerate`)
  - `GET /api/v1/export/estimates/excel` (bulk export)
  - All 4 debug endpoints
  - User CRUD endpoints (`POST`, `GET by ID`, `GET by email`, `PUT`)
- Added router prefix annotations for each section
- Noted production `/docs` and `/redoc` availability

### troubleshooting.md
- Added debug endpoint documentation (`/debug/database`, `/debug/external-api`, `/debug/headers`, `/debug/database/refresh`)
- Replaced stale "password in secret scope" troubleshooting with OAuth token-based approach
- Added CORS configuration troubleshooting
- Added API docs visibility section
- Removed reference to non-existent "auth redirect loop" issue

### database.md
- Completely rewritten `estimates` table with 5 missing columns: `customer_name`, `discount_config`, `original_prompt`, `is_deleted`, `updated_by`
- Completely rewritten `line_items` table with all workload-specific columns from `models/line_item.py`: `serverless_enabled`, `serverless_mode`, `dlt_edition`, all `dbsql_*` fields, all `vector_search_*` fields, `model_serving_gpu_type`, all `fmapi_*` fields, all `lakebase_*` fields, pricing tier/payment option fields, `workload_config` JSON
- Updated `users` table with `role` and `last_login_at` columns
- Added 5 missing tables: `templates`, `sharing`, `conversation_messages`, `decision_records`, and 13 pricing sync tables
- Updated `ref_workload_types` with all UI configuration flags from `models/workload_type.py`
- Replaced password-based DB access example with OAuth token-based approach
- Added indexes section

## How to Test

- **Docs build**: `cd docs-site && npm run build` (verified — builds cleanly)
- **Navigate**: Open any admin guide page in the built docs and verify content
- **Cross-reference**: Compare any admin guide page against the source file it documents

## Test Results

- `npm run build`: SUCCESS (zero errors, zero warnings)
- `pytest`: 1969 passed, 84 failed (all pre-existing), 2 skipped (143s)
- No new test failures introduced

## Known Limitations

- Screenshots are not included (this is a documentation content sprint, not a visual QA sprint)
- Debug endpoints may not be accessible in production (some require specific headers)
- The database.md pricing sync tables section lists tables created by the installer but doesn't detail every column

## Files Changed

- `docs-site/docs/admin-guide/deployment.md` — rewritten
- `docs-site/docs/admin-guide/configuration.md` — rewritten
- `docs-site/docs/admin-guide/installer.md` — rewritten
- `docs-site/docs/admin-guide/architecture.md` — rewritten
- `docs-site/docs/admin-guide/permissions.md` — updated
- `docs-site/docs/admin-guide/api-reference.md` — rewritten (20+ endpoints added)
- `docs-site/docs/admin-guide/troubleshooting.md` — rewritten
- `docs-site/docs/admin-guide/database.md` — rewritten (5 tables added, all schemas updated)
- `harness/contracts/sprint-5.md` — new
- `harness/handoffs/sprint-5-handoff.md` — new
- `harness/state.json` — updated
