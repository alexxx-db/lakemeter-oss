# Architecture

This document explains how Lakemeter is put together: what the major components are, how data flows between them, and where to look in the code when you need to change something. It assumes no prior familiarity with the project.

---

## 1. What Lakemeter is, in one paragraph

Lakemeter is a cost-estimation application for Databricks. A user describes the workloads they plan to run (for example: "a nightly ETL job on 8 workers of i3.xlarge for 2 hours"), and Lakemeter computes an estimated monthly cost in USD by combining two ingredients: (1) the Databricks unit price of the relevant SKU (DBUs — Databricks Units — or token rates), and (2) the underlying cloud VM price, when the workload runs on customer-managed ("classic") compute. The result is stored as an **estimate** containing **line items** (one per workload), and can be exported to a formatted Excel workbook.

The application runs as a **Databricks App** — a managed hosting environment inside a Databricks workspace — which gives it single sign-on (SSO) for free: anyone who can open the app is already authenticated by Databricks, and the backend learns their identity from headers the platform injects.

---

## 2. The moving parts at a glance

```
┌──────────────────────────────────────────────────────────────────────┐
│                        Databricks Workspace                           │
│                                                                       │
│  ┌─────────────────────┐        ┌──────────────────────────────────┐  │
│  │  Databricks Apps     │        │  Lakebase (managed PostgreSQL)   │  │
│  │  ┌────────────────┐  │        │                                  │  │
│  │  │ React frontend │  │        │  App tables (estimates, users…)  │  │
│  │  │ (static files) │  │        │  Pricing tables (sync_* / ref_*) │  │
│  │  └───────┬────────┘  │        │  SQL cost-calculation functions  │  │
│  │  ┌───────▼────────┐  │  SQL   │                                  │  │
│  │  │ FastAPI backend│──┼───────►│                                  │  │
│  │  └───────┬────────┘  │        └─────────────▲────────────────────┘  │
│  └──────────┼───────────┘                      │ synced (CDC)         │
│             │                                  │                      │
│             │ HTTPS              ┌─────────────┴────────────────────┐ │
│             ▼                    │  Unity Catalog                    │ │
│  ┌─────────────────────┐         │  lakemeter_catalog.lakemeter.*    │ │
│  │ Model Serving        │         │  (raw pricing, refreshed monthly)│ │
│  │ (Claude via FMAPI)   │         └──────────────────────────────────┘ │
│  └─────────────────────┘                                               │
└──────────────────────────────────────────────────────────────────────┘
```

Four runtime components:

| Component | Technology | Where it lives in the repo | What it does |
|---|---|---|---|
| Frontend | React + TypeScript + Tailwind + Vite | `frontend/` | Single-page app; built into static files served by the backend |
| Backend API | FastAPI + SQLAlchemy + Pydantic | `backend/app/` | REST API under `/api/v1`; serves the built frontend |
| Database | Lakebase (PostgreSQL) | provisioned by installer; schema in `scripts/notebooks/02_create_database.py` | Stores user data *and* the authoritative pricing tables |
| AI assistant | Claude via Databricks Foundation Model APIs | `backend/app/services/ai_agent.py`, `backend/app/routes/chat.py` | Turns natural language into suggested line items |

Plus two data pipelines that run *outside* the app, inside the workspace:

- **Pricing fetch pipeline** (`etl/pricing_sync/`) — notebooks that pull official Databricks list prices (from system tables) and cloud VM prices (from AWS/Azure/GCP price lists) into **Unity Catalog** tables under `lakemeter_catalog.lakemeter`.
- **Sync + setup pipeline** (`etl/lakebase_setup/`, and the installer variant in `scripts/notebooks/`) — creates the Lakebase database, tables, SQL functions, and copies the Unity Catalog pricing rows into Lakebase `sync_*` tables.

And one static artifact that ships with the app:

- **Bundled pricing snapshot** (`backend/static/pricing/`) — CSV/JSON files with the same pricing data, so the installer can seed a fresh database without running the fetch notebooks.

---

## 3. Request lifecycle: what happens when a user clicks "Calculate"

This is the single most important flow to understand. Follow it end to end and most of the codebase makes sense.

1. **The browser** sends `POST /api/v1/calculate/<workload>` (for example `/calculate/jobs`) with a JSON body describing one line item: node types, worker counts, hours per month, cloud, region, and so on. The request schemas live in `backend/app/routes/calculate/schemas.py`.

2. **The route handler** (for example `backend/app/routes/calculate/jobs.py`) validates the input and decides which pricing inputs it needs: DBU rate for the SKU, DBU-per-hour rate for each instance type, and (for classic compute) VM hourly costs.

3. **Pricing lookup** happens through `backend/app/services/lakebase_pricing.py`, which reads from the Lakebase `sync_*` / `ref_*` pricing tables. These tables are the runtime-authoritative source of pricing: the app never calls out to AWS/Azure/GCP price lists at request time. (A small set of static JSON files under `backend/static/pricing/` is used by some endpoints as fallback/reference data.)

4. **Cost math** is performed by SQL functions inside Lakebase itself (see §6), or in Python in the route handler for workload types that don't have a SQL function. The result is a structured cost breakdown: DBU count, DBU cost, VM cost, total.

5. **The response** is returned to the browser, and the caller (usually a line-item edit form) stores the full breakdown JSON back onto the line item's `cost_calculation_response` column when the user saves.

6. **Export** (`backend/app/routes/export/`) later reads all line items of an estimate and renders an Excel workbook with `openpyxl`/`xlsxwriter` using the stored breakdowns — it does not recalculate.

Why this design matters operationally: **all pricing data lives inside the customer's own workspace**, in their Lakebase database. The app makes zero external network calls at runtime for pricing. That is a deliberate security and reliability decision (see DECISIONS.md).

---

## 4. Backend structure (`backend/app/`)

```
backend/app/
├── main.py            # FastAPI app creation, middleware, router registration, static files
├── config.py          # Settings (env vars) + logging setup
├── database.py        # SQLAlchemy engine/session; OAuth token refresh for Lakebase
├── external_api.py    # Outbound API helpers (model serving etc.)
├── auth/              # Databricks SSO identity extraction + token management
├── models/            # SQLAlchemy ORM models (table definitions in Python)
├── schemas/           # Pydantic request/response models (the API contract)
├── routes/            # One module per API area (see below)
└── services/          # Business logic shared between routes
```

**Routers** are registered in `main.py`, all under the `/api/v1` prefix:

| Router | Prefix (relative) | Purpose |
|---|---|---|
| `estimates` | `/estimates` | CRUD for estimates; sharing |
| `line_items` | `/line-items` | CRUD for line items within an estimate |
| `workload_types` | `/workload-types` | The catalog of 16 workload types and which form fields each shows |
| `users` | `/users` | Current-user profile (self), admin updates, email lookup for sharing |
| `export` | `/export` | Excel generation |
| `vm_pricing` | `/vm-pricing` | VM price lookup endpoints for the UI |
| `calculate` | `/calculate/*` | One endpoint per workload type |
| `reference` | `/reference/*` | Dropdown data: clouds/regions, instance types, DBSQL sizes, FMAPI models… |
| `chat` | `/chat` | AI assistant streaming chat |

**Authentication.** `auth/databricks_auth.py` reads the user identity headers injected by the Databricks Apps proxy (`X-Forwarded-Email`, `X-Forwarded-User`) and upserts a row in the `users` table. `get_current_user` is a FastAPI dependency used by protected routes. There is **no** application-issued JWT; Apps SSO is the only identity path in production and local Apps-like testing.

**Database connection.** `database.py` builds a SQLAlchemy engine pointing at Lakebase. Preferred auth is the app Service Principal with short-lived OAuth database credentials (token refresh + cold-start retries). A secrets-backed password role (`lakemeter_sync_role`) remains as fallback. New/reused Lakebase Autoscaling projects enable Postgres native login (`enable_pg_native_login=True`) so that fallback can authenticate. `DB_SSLMODE=require` is set in `app.yaml` — always keep TLS on.

**Configuration.** Everything is an environment variable mapped in `config.py` (`Settings`). In the deployed app these come from `app.yaml`; locally, from a `.env` file. Notable ones: `DB_HOST`, `DB_USER`, `DB_NAME`, `DB_PORT`, `LAKEBASE_INSTANCE_NAME`, `CLAUDE_MODEL_ENDPOINT`, `ENVIRONMENT`.

---

## 5. Frontend structure (`frontend/src/`)

```
frontend/src/
├── main.tsx       # Entry point; mounts <App/>
├── App.tsx        # Routes (react-router)
├── pages/         # Top-level screens (Home, Estimate detail, Admin…)
├── components/    # Reusable UI (forms per workload type, tables, dialogs)
├── hooks/         # React hooks (data fetching, debouncing…)
├── store/         # Client-side state
├── api/           # Fetch wrappers around /api/v1 endpoints
├── types/         # TypeScript types mirroring the backend schemas
├── utils/         # Formatting, math helpers
└── version.ts     # APP_VERSION constant shown in the footer
```

Two things worth knowing:

- **The frontend is served by the backend.** `vite build` emits to `backend/static/`, and FastAPI serves those files. There is no separate web server in production. `CORS_ORIGINS` is empty in production (`app.yaml`) because frontend and API share an origin.
- **The workload forms are data-driven.** The `ref_workload_types` table (exposed via `/api/v1/workload-types`) carries `show_*` boolean flags (`show_compute_config`, `show_photon_toggle`, `show_usage_tokens`, …) that tell the UI which inputs to render for each workload type. Adding a new workload type is mostly: seed a row, add a calculate endpoint, add a form component.

---

## 6. The database is also a calculation engine

Unusually for a web app, a large part of the cost math lives **inside PostgreSQL as SQL functions**. They are created from `scripts/functions/` (numbered `01`–`09`; there is no `07`) by the installer notebook `scripts/notebooks/02b_create_functions.py`:

| File | Functions (schema `lakemeter`) | Role |
|---|---|---|
| `01_Utility_Functions.py` | `calculate_hours_per_month`, `get_product_type_for_pricing`, `get_dbu_price`, `get_photon_multiplier` | Shared helpers: usage math, SKU selection, price lookup, Photon uplift |
| `02_DBU_Calculators_Classic.py` | `calculate_classic_compute_dbu` | DBUs for Jobs/All-Purpose/DLT classic clusters |
| `03_DBU_Calculators_Serverless.py` | `calculate_serverless_compute_dbu` | DBUs for serverless compute |
| `04_DBU_Calculators_DBSQL.py` | `calculate_dbsql_dbu` | Warehouse DBUs (classic/pro/serverless) |
| `05_DBU_Calculators_Vector_Model.py` | `calculate_vector_search_dbu`, `calculate_model_serving_dbu` | Serverless product rates |
| `06_DBU_Calculators_FMAPI.py` | `calculate_fmapi_databricks_dbu`, `calculate_fmapi_proprietary_dbu` | Token-based LLM costs |
| `08_VM_Cost_Calculators.py` | `calculate_classic_vm_costs`, `calculate_dbsql_vm_costs` | Cloud VM cost for customer-managed compute |
| `09_Main_Orchestrator.py` | `calculate_line_item_costs` | One entry point that dispatches to the right calculator given a line item's workload type |

Why SQL functions at all? Two reasons. First, the same calculation can then be used from notebooks, SQL editor, and the app — the cost model is defined once, in the database where the pricing data already lives. Second, it makes the cost model auditable: an engineer can `SELECT lakemeter.calculate_line_item_costs(...)` by hand to reproduce any number the app produced. The detailed table-by-table design is in SCHEMA.md.

The `calculate` routes call these functions where available and fall back to equivalent Python math for workload types without a SQL calculator (e.g. Lakebase CU pricing, AI Parse, Shutterstock, Databricks Apps, Lakeflow Connect).

---

## 7. The pricing data pipeline, end to end

Pricing is the product's foundation, so it has three redundant representations, each with a distinct job:

```
 Official sources                       Where it's kept             Who reads it
────────────────────────────────────────────────────────────────────────────────
 system.billing.list_prices  ─┐
 AWS/Azure/GCP price lists    ├─►  Unity Catalog:            ─►  Lakebase sync (CDC)
 (fetched monthly by          │   lakemeter_catalog.lakemeter     copies rows into
  etl/pricing_sync/)          │   (raw, workspace-owned)          Lakebase sync_* tables
 Instance Type Pricing.xlsx  ─┘                                      │
                                                                     ▼
                                              Lakebase: sync_pricing_dbu_rates,
                                              sync_pricing_vm_costs,
                                              sync_product_* , sync_ref_*    ─► app runtime
 Bundled snapshot in git (backend/static/pricing/*.csv|json)
        │                                                                  ▲
        └──► installer seeds a fresh Lakebase (03_load_pricing_data.py) ───┘
```

1. **Unity Catalog layer** (`etl/pricing_sync/`): notebooks fetch official prices into `lakemeter_catalog.lakemeter.*` tables. This is the *source of record* inside a workspace and the place where data-quality checks (`99_Debug_Data_Quality.ipynb`) run.
2. **Lakebase `sync_*` layer**: a Lakebase sync (CDC) mirrors those UC tables into the app's database with a `sync_` prefix, and the installer can load the same data from the bundled CSVs. These tables are what the SQL functions and the app read at runtime.
3. **Bundled snapshot** (`backend/static/pricing/`): versioned in git, shipped with each release, loaded idempotently by `scripts/notebooks/03_load_pricing_data.py` (`CREATE TABLE IF NOT EXISTS` + `TRUNCATE` + bulk insert; the notebook hard-fails if expected CSVs are missing). This makes a fresh install work even before the fetch notebooks have ever run, and anchors pricing to the release version.

A scheduled job (`lakemeter_pricing_refresh` in `scripts/databricks.yml`, weekly Sunday 06:00 UTC, **paused by default**) reloads pricing via `09_refresh_pricing.py`. Default source is bundled CSVs; set job parameter `pricing_source=unity_catalog` to publish from UC tables (`10_refresh_pricing_from_uc.py`). See `docs-site/docs/admin-guide/pricing-data.md`.

---

## 8. Deployment topology

Everything is deployed by **Databricks Asset Bundles** (`scripts/databricks.yml`), driven by `scripts/install.sh`:

1. `01_provision_lakebase.py` — create the Lakebase instance (autoscaling).
2. `02_create_database.py` — database `lakemeter_pricing`, schema `lakemeter`, app tables, triggers, the `lakemeter_sync_role` login role with **least-privilege** grants (`scripts/lakebase_grants.py`), and secrets (`lakebase-user`, `lakebase-password`, `lakebase-host`, `lakebase-database`) in a secrets scope.
3. `02b_create_functions.py` — the SQL calculators from §6.
4. `03_load_pricing_data.py` — seed pricing from the bundled snapshot.
5. `04_create_sku_mapping.py` — SKU→region mapping.
6. `05a/05b` — create the Databricks App and grant it access.
7. `06_deploy_app.py` — build the frontend (`tsc && vite build`), package the app, deploy.
8. `07_verify_installation.py` — smoke checks.

At runtime the platform injects `DATABRICKS_HOST`, `DATABRICKS_CLIENT_ID`, `DATABRICKS_CLIENT_SECRET` into the app; the app's own service principal authenticates to Lakebase and to the model-serving endpoint. The app itself binds to `0.0.0.0:${DATABRICKS_APP_PORT}` via uvicorn (see `app.yaml`).

---

## 9. Where to look when you want to change X

| You want to… | Start here |
|---|---|
| Change how a workload's cost is computed | `scripts/functions/0X_*.py` (SQL) **and** the matching `backend/app/routes/calculate/*.py` |
| Add/adjust an API endpoint | `backend/app/routes/` + request/response types in `backend/app/schemas/` |
| Add a column to estimates or line items | `scripts/notebooks/02_create_database.py` (migration list), `backend/app/models/`, `backend/app/schemas/` |
| Update prices | re-run `scripts/notebooks/03_load_pricing_data.py` (or the monthly job); bump the bundled snapshot for a release |
| Add a workload type | `ref_workload_types` seed + `calculate` route + frontend form + SQL calculator |
| Change the Excel output | `backend/app/routes/export/excel_*.py` |
| Change the AI assistant | `backend/app/services/ai_agent.py`, `backend/app/routes/chat.py`, `CLAUDE_MODEL_ENDPOINT` |
| Change deployment/infra | `scripts/databricks.yml`, `scripts/install.sh`, `scripts/notebooks/0X_*.py` |

---

## 10. Testing layout

`tests/` mirrors the backend: unit tests per route/service, plus `tests/export/golden/` (a pinned canonical estimate whose every number is independently derived — change the cost model and these tests tell you exactly what moved), `tests/test_pricing_data_clouds.py` (36 checks that the bundled pricing snapshot covers all three clouds), `tests/test_version_sync.py` (version strings consistent across the repo), `tests/test_health_diagnostics.py`, and `tests/test_telemetry.py`. E2E and credential-gated suites (`tests/e2e/`, `tests/ai_assistant/`) require a live workspace and are excluded from CI by default.
