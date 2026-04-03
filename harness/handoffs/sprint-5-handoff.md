# Sprint 5 Handoff: Admin Guide Accuracy & Update (Iteration 2)

## What Was Built

### Iteration 1 (prior)
All 8 admin guide pages were audited against the current codebase and rewritten for accuracy. See iteration 1 handoff for full details.

### Iteration 2 (this iteration)
Thorough verification pass of all 8 admin guide pages against source code. One significant gap found and fixed:

**api-reference.md — Added ~20 missing frontend convenience endpoints:**
- `GET /api` — API root info
- `GET /api/v1/regions?cloud=` — Regions by cloud from SKU region map
- `GET /api/v1/reference/clouds` — Cloud providers with regions from DB
- `GET /api/v1/reference/tiers` — Pricing tiers
- `GET /api/v1/instances/types?cloud=` and `/reference/instance-types/{cloud}` — Instance types
- `GET /api/v1/instances/families` — Instance family categories
- `GET /api/v1/instances/vm-costs` — VM cost proxy to external API
- `GET /api/v1/dbsql/warehouse-sizes` and `/reference/dbsql-sizes` — DBSQL sizes
- `GET /api/v1/dbsql/warehouse-types` — Warehouse types
- `GET /api/v1/dlt/editions` and `/reference/dlt-editions` — DLT editions
- `GET /api/v1/serverless/modes` — Serverless mode options
- `GET /api/v1/model-serving/gpu-types?cloud=` and `/reference/model-serving-gpu-types/{cloud}` — GPU types
- `GET /api/v1/photon/multipliers?cloud=` — Photon multipliers
- `GET /api/v1/fmapi/databricks-models/list` — FMAPI model list
- `GET /api/v1/reference/fmapi-models` — Foundation models (legacy)
- `GET /api/v1/reference/fmapi-databricks` — FMAPI Databricks config
- `GET /api/v1/reference/fmapi-proprietary` — FMAPI Proprietary config
- `GET /api/v1/pricing/dbu-rates?cloud=&region=&tier=` — DBU rate lookup
- `GET /api/v1/pricing/product-types?cloud=&region=&tier=` — Product types

These endpoints are defined directly in `main.py` (not via routers) and were not covered in the iteration 1 API reference, which only documented router-based endpoints.

### Verification Results (All 8 Pages)
- **deployment.md** — Verified against `deploy.sh` and both `app.yaml` files. Accurate.
- **configuration.md** — Verified against `app/config.py` Settings class. All env vars match.
- **installer.md** — Verified against `install_lakemeter.py`. 9-step flow matches.
- **architecture.md** — Verified against actual file tree (`backend/app/` routes, models, auth, services, schemas). All directories and files match.
- **permissions.md** — Verified against `token_manager.py` and `database.py`. Token lifecycle accurate.
- **api-reference.md** — Fixed. Now documents all endpoints from both routers and `main.py`.
- **troubleshooting.md** — Verified debug endpoints exist in `main.py`. All 4 debug endpoints documented.
- **database.md** — Verified against `models/line_item.py` and other model files. All columns match.

## How to Test

- **Docs build**: `cd docs-site && npm run build` (verified — builds cleanly, zero errors)
- **Navigate**: Open any admin guide page and cross-reference against the source file it documents
- **API reference**: Compare the new "Frontend Data Endpoints" section against `grep -n "@app.get" backend/app/main.py`

## Test Results

- `npm run build`: SUCCESS (zero errors, zero warnings)
- `pytest`: 1969 passed, 84 failed (all pre-existing in `test_workload_coverage.py`), 2 skipped (142s)
- No new test failures introduced

## Known Limitations

- Screenshots are not included (documentation content sprint)
- The frontend convenience endpoints in `main.py` have some overlap/duplication with router-based endpoints in `routes/reference.py` — this is by design for frontend store compatibility
- Some GPU DBU rates in `main.py` hardcoded endpoints may not exactly match values in the Lakebase `sync_product_serverless_rates` table (hardcoded fallbacks vs. DB values)

## Files Changed

- `docs-site/docs/admin-guide/api-reference.md` — Added "Frontend Data Endpoints" section with ~20 missing endpoints
- `harness/handoffs/sprint-5-handoff.md` — Updated
- `harness/state.json` — Updated
