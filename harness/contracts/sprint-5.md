# Sprint 5 Contract: Admin Guide Accuracy & Update

## Acceptance Criteria

### deployment.md
- [ ] `app.yaml` snippet matches actual `app.yaml` (root-level, includes SP key names and DB_PORT/DB_SSLMODE)
- [ ] Deploy command matches `deploy.sh` behavior (frontend build via npm ci, docs build, `databricks apps deploy`)
- [ ] Deployment steps reference `deploy.sh` as the primary method, with manual steps as alternative
- [ ] Docs/production distinction noted (docs_url disabled in production)
- [ ] Authentication section describes SSO headers + SP OAuth M2M accurately

### configuration.md
- [ ] Environment variable table matches `app/config.py` Settings class exactly
- [ ] Secret scope section reflects `valueFrom` pattern in `app.yaml`, not direct secret scope keys
- [ ] `DB_PORT` and `DB_SSLMODE` hardcoded values listed
- [ ] SP_CLIENT_ID_KEY and SP_SECRET_KEY explained correctly (key names, not values)
- [ ] CORS explanation matches `cors_origins_list` property behavior

### installer.md
- [ ] 9-step flow matches actual `install_lakemeter.py` steps
- [ ] Step 1 prereqs: Python 3.10+, psycopg2-binary, databricks-sdk, requests, Node.js (optional)
- [ ] Step 2 config params match `gather_config()` function: instance_name, db_name, app_name, cu_size, secrets_scope, sp_client_id_key, sp_secret_key
- [ ] Step 3 describes Lakebase provisioning via databricks-sdk `database.create_database_instance`
- [ ] Steps 4-9 align with actual code (create DB/schema, load pricing, SKU mapping, SP access, views, generate app.yaml)
- [ ] CLI flags documented: `--profile`, `--skip-provision`, `--skip-deploy`

### architecture.md
- [ ] Backend structure matches actual file tree (all routes, models, services, auth/ directory)
- [ ] Frontend structure mentions all key files (api/client.ts, pages, store, utils, types)
- [ ] Export module shown as modular (11 files in routes/export/)
- [ ] Auth module shown (auth/token_manager.py, auth/databricks_auth.py)
- [ ] Data flow for cost calculation, export, and AI assistant are accurate
- [ ] Tech stack table matches actual deps (requirements.txt, package.json)

### permissions.md
- [ ] SP OAuth M2M flow documented with correct API paths
- [ ] 3 permission layers: workspace, instance (Roles API), schema (SQL grants) documented
- [ ] Token lifecycle matches `database.py` behavior (pool_recycle=900, 30-min engine refresh)
- [ ] `identity_type=SERVICE_PRINCIPAL` critical finding retained
- [ ] Test list matches actual test file contents

### api-reference.md
- [ ] All route prefixes match actual routers: /estimates, /line-items, /workload-types, /users, /export, /vm-pricing, /calculate, /reference, /chat
- [ ] All endpoints listed match `@router.get/post/put/delete` decorators in source
- [ ] Missing endpoints added: /estimates/me/info, /line-items/{id}/clone, /chat/{id}/state, /chat/{id}/confirm-workload, /vm-pricing/*, /reference/regions, /reference/pricing-bundle/*
- [ ] Response schemas reference actual Pydantic schema names
- [ ] Health endpoint at /health documented

### troubleshooting.md
- [ ] OAuth token refresh described (30-min engine refresh cycle from database.py)
- [ ] SP credential troubleshooting references `identity_type=SERVICE_PRINCIPAL`
- [ ] Lakebase connection issues reference `token_manager.py`
- [ ] No references to non-existent debug endpoints (verify they exist before documenting)

### database.md
- [ ] Estimates table schema matches `models/estimate.py` (customer_name, discount_config missing from current doc)
- [ ] Line items schema matches `models/line_item.py` (serverless_enabled, serverless_mode, dlt_edition, dbsql_* fields, vector_search_*, model_serving_*, fmapi_*, lakebase_*, pricing tier fields)
- [ ] Users table matches `models/user.py` (role, last_login_at fields)
- [ ] All model tables listed: User, Estimate, LineItem, Template, RefWorkloadType, Sharing, ConversationMessage, DecisionRecord, VMPricing, SKURegionMap, InstanceDBURates
- [ ] Database connection section describes OAuth token-based connection, not password-based

## Test Plan
- `cd docs-site && npm run build` succeeds with zero errors
- All internal links in admin guide pages resolve
- Existing test suite passes (`pytest` from project root)

## Files to Change
- `docs-site/docs/admin-guide/deployment.md`
- `docs-site/docs/admin-guide/configuration.md`
- `docs-site/docs/admin-guide/installer.md`
- `docs-site/docs/admin-guide/architecture.md`
- `docs-site/docs/admin-guide/permissions.md`
- `docs-site/docs/admin-guide/api-reference.md`
- `docs-site/docs/admin-guide/troubleshooting.md`
- `docs-site/docs/admin-guide/database.md`
