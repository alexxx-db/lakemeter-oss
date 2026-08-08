# Decisions

Architecture Decision Records (ADRs) for Lakemeter. Each entry follows the same shape: **Context** (what situation forced a choice), **Decision** (what we chose), **Consequences** (what that choice costs and buys), **Alternatives considered** (what we rejected and why). Read these before proposing to change something fundamental — the trade-offs were usually deliberate.

---

## ADR-001: Run as a Databricks App, not a standalone web service

**Context.** The tool's users already live inside Databricks workspaces, and its data (prices) is workspace data. Hosting options ranged from "generic container on any cloud" to "fully inside the workspace."

**Decision.** Lakemeter is packaged and deployed exclusively as a Databricks App, installed via Databricks Asset Bundles (`scripts/install.sh` + `scripts/databricks.yml`).

**Consequences.** (+) SSO comes free — the Apps platform authenticates every visitor and injects identity headers; no login screens, no user database to bootstrap. (+) The app's service principal gets platform-managed credentials (`DATABRICKS_CLIENT_ID/SECRET` auto-injected), so there are no long-lived secrets to rotate for workspace access. (+) One-command install. (−) The app cannot run meaningfully outside Databricks; local development needs shims (JWT fallback auth, a local Postgres). (−) Release cadence is tied to Apps platform capabilities.

**Alternatives considered.** Standalone container behind a corporate IdP: rejected because it duplicates authentication, networking, and secrets management that the platform already provides, and because all pricing data is in-workspace anyway.

---

## ADR-002: Lakebase (PostgreSQL) is the single runtime database — for both app data and pricing data

**Context.** Estimates need OLTP storage; pricing needs bulk analytical reads. These could have been split (e.g. Delta tables for pricing, Postgres for app state).

**Decision.** One Lakebase database (`lakemeter_pricing`, schema `lakemeter`) holds the application tables (`users`, `estimates`, `line_items`, …) *and* the runtime pricing tables (`sync_pricing_dbu_rates`, `sync_pricing_vm_costs`, `sync_product_*`, `sync_ref_*`). Unity Catalog remains the upstream source of record for raw pricing; Lakebase holds the synced copy the app reads (see ADR-003).

**Consequences.** (+) One connection string, one backup story, one permission model. (+) Joins between line items and pricing tables happen inside the database — which is what makes the SQL calculators (ADR-004) possible. (−) The pricing snapshot adds ~110k rows to an OLTP database; acceptable at this scale, and reads are indexed.

**Alternatives considered.** Read pricing directly from Unity Catalog via SQL warehouses: rejected — adds a warehouse dependency and cold-start latency to every calculation, and breaks the "app must not depend on a running warehouse" constraint.

---

## ADR-003: The app never calls external pricing APIs at request time

**Context.** Databricks list prices live in system tables; VM prices live in AWS/Azure/GCP price-list APIs. The freshest possible data would be fetched live, per calculation.

**Decision.** Pricing is fetched **offline** by the `etl/pricing_sync/` notebooks into Unity Catalog, synced into Lakebase `sync_*` tables, and additionally **snapshotted into git** (`backend/static/pricing/`) with each release. At request time the app reads only its own database (plus bundled static files as reference). A monthly scheduled job (paused by default) refreshes the Lakebase copy.

**Consequences.** (+) Zero runtime egress — important for security review and for workspaces with locked-down networking. (+) Calculations are reproducible: a given release always produces the same numbers until pricing is deliberately refreshed. (+) No rate limits or cloud-API credentials in the app. (−) Prices can go stale between refreshes; mitigated by the monthly job, the release-cadence snapshot updates, and tracking issues for known data events (e.g. model-family retirements).

**Alternatives considered.** Live per-request price fetching: rejected on reliability, latency, and egress grounds.

---

## ADR-004: Cost math lives in the database as SQL functions

**Context.** Cost formulas must be consistent everywhere they're used — the app, notebooks, ad-hoc SQL audits. Duplicating formulas in Python and SQL invites drift.

**Decision.** Core DBU and VM cost formulas are implemented once, as PostgreSQL functions in the `lakemeter` schema (`scripts/functions/01–09`, orchestrated by `calculate_line_item_costs`). Python route handlers call them; workload types without a SQL calculator use equivalent Python math in `backend/app/routes/calculate/`.

**Consequences.** (+) One definition of each formula, co-located with the data. (+) Auditable — any engineer can reproduce a number with a hand-written `SELECT`. (+) Testable from both SQL (`etl/lakebase_setup/tests/`) and Python. (−) Two languages in the calculation path; contributors must keep SQL and any Python fallbacks in sync. (−) Schema/function changes require database migrations, not just an app redeploy.

**Alternatives considered.** All math in Python: rejected because notebooks and SQL users would then have no access to the cost model, and because join-heavy pricing lookups are cheaper inside the database.

---

## ADR-005: Database migrations are idempotent notebooks, not a migration framework

**Context.** The installer already runs notebooks; introducing Alembic/Flyway adds a tool most workspace admins don't have.

**Decision.** Schema evolution is expressed as `CREATE TABLE IF NOT EXISTS`, `ALTER TABLE ... ADD COLUMN IF NOT EXISTS`, and `CREATE OR REPLACE FUNCTION` inside the installer notebooks (`02_create_database.py` carries an explicit `migration_columns` list for older installations). Every step is safe to re-run.

**Consequences.** (+) Re-running the installer *is* the upgrade path — no separate "migrate" command. (+) Works with nothing but a Databricks workspace. (−) No down-migrations; rollback means restoring data, not reversing DDL. (−) Column removals/renames need hand-written release steps (kept in `etl/lakebase_setup/release_*/`).

**Alternatives considered.** Alembic: rejected — operational burden for admins, and Lakebase connections use short-lived OAuth tokens that complicate offline migration runners.

---

## ADR-006: Case normalization is enforced by database triggers

**Context.** Pricing joins are case-sensitive (`cloud='AWS'` vs `'aws'`), while data arrives from many sources (UI forms, AI assistant, API clients) with inconsistent casing. Cleaning at every call site had already produced bugs (see `etl/lakebase_setup/debug/`).

**Decision.** `BEFORE INSERT OR UPDATE` triggers on `estimates` and `line_items` normalize canonical casing: enum-like fields upper-cased (`cloud`, `tier`, `workload_type`, `dbsql_warehouse_type`, `dlt_edition`), descriptive/mode fields lower-cased (`serverless_mode`, `vector_search_mode`, `fmapi_*`, `model_serving_gpu_type`, pricing tiers).

**Consequences.** (+) Impossible to write badly-cased data through any path, including ones we didn't anticipate. (+) Pricing joins can assume canonical case. (−) Trigger behavior is invisible to people reading only application code — this ADR and SCHEMA.md are the documentation. (−) New enum-like columns must be added to the trigger function explicitly.

**Alternatives considered.** Normalization in Pydantic validators only: rejected because it doesn't cover writes from notebooks, SQL editor, or future API clients.

---

## ADR-007: The bundled pricing snapshot is versioned in git and loaded idempotently

**Context.** A fresh install needs pricing data immediately, but the fetch notebooks require cloud API access and take time. Releases also need a reproducible answer to "what prices did this version assume?"

**Decision.** The pricing snapshot ships inside the repo at `backend/static/pricing/` (CSV/JSON; large files split into `*_partN.csv`). The loader (`03_load_pricing_data.py`) recreates tables if absent, `TRUNCATE`s, bulk-inserts, and **hard-fails if expected files are missing** — a partial pricing load is never silently accepted.

**Consequences.** (+) Air-gapped install path. (+) Pricing diffs are reviewable in pull requests. (+) Release N always implies a specific price list. (−) Repo size; mitigated by CSV split parts and compression-friendly formats.

---

## ADR-008: Frontend served by the FastAPI backend (no separate web tier)

**Context.** Databricks Apps runs one container. A separate static hosting tier would need a second endpoint and CORS.

**Decision.** `vite build` outputs to `backend/static/`; FastAPI serves it. Production `CORS_ORIGINS` is empty (same-origin only).

**Consequences.** (+) One process, one URL, no CORS surface in production. (+) Version skew between frontend and backend is impossible within a deployment. (−) API and static traffic share one process; fine at app scale.

---

## ADR-009: Version is a single source of truth, pinned by tests

**Context.** The version appears in `VERSION`, `frontend/package.json`, `docs-site/package.json`, both lockfiles, `frontend/src/version.ts`, and the changelog. Manual bumps drift.

**Decision.** `VERSION` at repo root is canonical; `tests/test_version_sync.py` fails CI if any copy disagrees or if the latest changelog entry is undated. `scripts/update_version.py` performs the bump; `RELEASING.md` documents the flow.

**Consequences.** (+) Drift is caught before release, not after. (−) One more test to understand when it fails — the failure message names the drifted files and the fix command.

---

## ADR-010: Observability is opt-in and self-hosted-first

**Context.** Productionalizing required health signal and (optionally) usage telemetry, without compromising the zero-egress posture of ADR-003.

**Decision.** Readiness and diagnostics endpoints (`/health/ready`, `/api/v1/diagnostics`) report DB reachability, pricing-table population, and config with secrets masked. Structured JSON logging is available via `LOG_FORMAT=json`. Telemetry is **off unless both** `TELEMETRY_ENABLED` and `TELEMETRY_ENDPOINT` are set; payloads contain only scalars and a salted, truncated hash of the workspace host; sending is fire-and-forget and can never break a request.

**Consequences.** (+) Deployers get the signal they need with no default egress. (−) Two config knobs must be set for telemetry; that is intentional friction.

---

## ADR-011: Golden-estimate tests pin the cost model

**Context.** Cost-model changes are easy to make and hard to notice. A refactor that silently shifts a number by 2% is the worst kind of bug for a pricing tool.

**Decision.** `tests/export/golden/` contains a canonical 9-workload estimate whose expected values are derived independently of the implementation. Any change to calculators, pricing data shape, or export math that alters the canonical estimate fails these tests loudly.

**Consequences.** (+) Refactors are safe; intentional model changes require deliberately updating the golden pack, which forces a review conversation. (−) Golden values must be re-derived when the cost model legitimately changes.

---

## ADR-012: Live FinOps is a separate actuals plane (not Lakebase OLTP)

**Context.** Lakemeter today answers “what might this cost?” using snapshot list prices in Lakebase (ADR-002, ADR-003). Customers also need “what did we spend?” from Databricks billable usage. Stuffing account-scale `system.billing.usage` into Lakebase would fight OLTP sizing, cold-start, and the zero-egress estimator posture. Replacing the estimator with a Genie dashboard would discard transparent sizing + Excel export.

**Decision.** Live FinOps is a **second product plane** next to the estimator:

1. **Source of truth for actuals** is Databricks system tables: `system.billing.usage` joined to `system.billing.list_prices` on `sku_name` with a **price time-window** (`usage_end_time` ∈ `[price_start_time, price_end_time)`). Always retain `billing_origin_product` alongside `sku_name`.
2. **Gold layer** lives in Unity Catalog (`{catalog}.lakemeter_finops.*`), built by a scheduled Lakeflow Job under `etl/finops/` (P0 scaffold). Default dollars are **list cost**; commercial/negotiated overlays are explicit and labeled — never presented as the invoice.
3. **Serving** is a SQL warehouse (App SP read-only SELECT on gold). Optional later: Genie/Lakeview for exploration; rolled-up KPI sync into Lakebase only if App latency requires it.
4. **Estimator path unchanged.** ADR-003 still holds for estimate calculations — the App does not call billing system tables at request time for sizing. Variance (estimate ↔ actual) is a later phase and requires a tagging contract (`lakemeter_estimate_id`, …) or an explicit resource map; unattributed spend stays visible.

**Consequences.** (+) Clear separation of planning OLTP vs account-scale analytics. (+) Auditable join semantics matching Databricks FinOps guidance. (+) Installer/estimator remains usable without system-table enablement. (−) Two data planes and an extra warehouse permission to operate. (−) List cost ≠ customer invoice until a rate card is applied. (−) Variance quality depends on tag hygiene.

**Alternatives considered.**

- *Pipe raw usage into Lakebase:* rejected — wrong store for high-volume billing facts; breaks ADR-002 scale assumptions.
- *Live per-request system-table queries from the App:* rejected — warehouse cold-start, privilege sprawl, and couples every Actuals page load to account billing access.
- *Replace Lakemeter with Lakeview/Genie only:* rejected — loses the sizing/export product; Genie remains optional exploration, not the estimator.
- *Invoice-accurate dollars from list_prices alone:* rejected — `list_prices` is not the contract; commercial overlay must be explicit.

**Delivery phases (product).** P0 gold job (`etl/finops`); P1 Actuals UI (`/actuals`); P2 estimate↔actual variance via `lakemeter_estimate_id` tags (`cost_by_estimate_daily` + `/finops/variance/{id}`); P3 chargeback/budgets. See design canvas `lakemeter-live-finops-design` and `etl/finops/TAGGING.md`.
