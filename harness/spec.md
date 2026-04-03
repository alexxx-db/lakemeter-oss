# Lakemeter — Installation, Integration & Documentation Validation Sprint

## Vision

Special-purpose validation sprint focused on three critical areas of the Lakemeter app after the Lakebase customer deployment feature landed (commit `fa55995`). This sprint validates the NEW installer (`scripts/install_lakemeter.py`), the SP OAuth M2M authentication via Roles API, the full 1419-test regression suite, and produces comprehensive documentation covering the deployment pipeline, permission model, and installer flow.

## Mode

**VALIDATION_AND_DOCS** — No new features. Three parallel workstreams: Installation testing, Integration/regression testing, and Documentation generation. Each workstream is a sprint with its own acceptance criteria.

## Environment

- **Databricks CLI profile**: `lakemeter`
- **Workspace**: `https://fe-vm-lakemeter.cloud.databricks.com`
- **Lakebase instance**: `lakemeter-customer`
- **Lakebase host**: `ep-silent-fire-d1kv74l0.database.us-west-2.cloud.databricks.com`
- **App name**: `lakemeter-api`
- **App URL**: `https://lakemeter-api-335310294452632.aws.databricksapps.com`
- **Secrets scope**: `lakemeter-secrets`

## Key Technical Context

### SP Roles API — Critical Finding
The Lakebase Roles API (`/api/2.0/database/instances/{name}/roles`) requires `identity_type: "SERVICE_PRINCIPAL"` when creating roles for Service Principals. Using `CREATE ROLE` SQL or `identity_type: "PG_ONLY"` does NOT grant OAuth M2M token exchange. This is a critical deployment requirement documented in `scripts/install_lakemeter.py`.

### app.yaml — valueFrom Pattern
Five env vars use Databricks Apps `valueFrom` resource references (not hardcoded values):
- `DATABRICKS_SECRETS_SCOPE` → `lakemeter-secrets-scope`
- `LAKEBASE_INSTANCE_NAME` → `lakemeter-lakebase-instance`
- `DB_HOST` → `lakemeter-db-host`
- `DB_USER` → `lakemeter-db-user`
- `DB_NAME` → `lakemeter-db-name`

### Installer — 9-Step Flow
1. Validate prerequisites (CLI, profile, secrets)
2. Gather configuration (interactive prompts)
3. Provision Lakebase instance (or skip with `--skip-provision`)
4. Create database, schema, tables, views, constraints
5. Load pricing reference data from `backend/static/pricing/`
6. Create SKU discount mapping
7. Configure SP access (OAuth M2M via Roles API)
8. Create cost calculation views
9. Generate app configuration (app.yaml with valueFrom refs)

### Permission Tests — 10 Tests
File: `tests/test_lakebase_permissions.py` — 5 test classes, 10 tests:
- Token generation (2): SP token generation + expiry validation
- DB connection (2): connectivity + PG16 version check
- Read access (3): workload types (9 expected) + DBU rates + VM costs
- Write access (1): full CRUD on users table
- Token refresh (1): auto-refresh after invalidation
- App health (1): FastAPI health endpoint with DB connection

## Features by Sprint

### Sprint 1: Installation Testing
Run `install_lakemeter.py --skip-provision --profile lakemeter` against the existing `lakemeter-customer` instance. Verify all 9 steps complete successfully. Validate pricing data loads correctly (workload types, DBU rates, VM costs, SKU mappings). Verify app.yaml generation with correct valueFrom references. Test error handling for missing prerequisites.

**Acceptance Criteria:**
- Installer runs end-to-end with `--skip-provision` (instance already exists)
- All 9 steps report success (green checkmarks)
- Pricing reference data loaded: 9 workload types, DBU rates > 0, VM costs > 0
- Generated app.yaml matches expected valueFrom pattern
- SP role created with `identity_type=SERVICE_PRINCIPAL` (not PG_ONLY)
- Clean exit code 0

### Sprint 2: Integration & Regression Testing
Run the full pytest suite (1419 tests). Run the 10 Lakebase permission tests separately. Verify SP can connect to Lakebase via OAuth M2M. Verify app health endpoint works with new config. Cross-feature regression across all 9 workload types + multi-workload scenarios + AI assistant.

**Acceptance Criteria:**
- Full pytest suite: 1419+ tests pass (excluding network-dependent tests that skip)
- Permission tests: 10/10 pass (token gen, DB connect, read, write, refresh, health)
- SP OAuth flow: token generation → DB connection → query execution verified
- App health endpoint returns 200 with healthy DB status
- No regressions in any workload type (JOBS, ALL_PURPOSE, DLT, DBSQL, MODEL_SERVING, VECTOR_SEARCH, FMAPI_DATABRICKS, FMAPI_PROPRIETARY, LAKEBASE)
- Multi-workload scenarios pass (sprints 10-11 test suites)

### Sprint 3: Documentation
Document the installer flow, SP Roles API finding, deployment steps, permission test coverage, and app.yaml configuration. Update existing docs-site with new deployment and admin guides.

**Acceptance Criteria:**
- Installer guide: complete 9-step walkthrough with `--skip-provision` usage
- SP Roles API documentation: the critical `identity_type=SERVICE_PRINCIPAL` finding with why `CREATE ROLE` SQL doesn't work
- Deployment guide: end-to-end deployment steps from clean state
- Permission test coverage: what each of the 10 tests verifies and why
- app.yaml reference: valueFrom pattern explained with all 5 resource references
- Docs site builds successfully (`cd docs-site && npm run build`)

## References
- Installer: `scripts/install_lakemeter.py` (1299 lines)
- Permission tests: `tests/test_lakebase_permissions.py` (237 lines)
- App config: `app.yaml` (41 lines)
- Token manager: `backend/app/auth/token_manager.py`
- Existing docs: `docs-site/docs/`
