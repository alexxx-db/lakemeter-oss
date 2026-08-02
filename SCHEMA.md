# Schema Specification

This document specifies every persistent data structure Lakemeter uses, at both
layers of the system:

- **Unity Catalog (UC)** — the workspace's source of record for raw pricing
  (`lakemeter_catalog.lakemeter.*`), produced by the fetch notebooks.
- **Lakebase (PostgreSQL)** — the app's runtime database (`lakemeter_pricing`,
  schema `lakemeter`), holding application tables, the synced pricing copy, and the
  SQL cost-calculation functions.

It also covers the governance model: who owns what, how access is granted, and the
naming conventions every new object must follow. When you add a table, column, or
function, update this file in the same pull request.

---

## 1. Naming and layering conventions

| Prefix / pattern | Layer | Meaning | Examples |
|---|---|---|---|
| *(none)* | Lakebase | Application tables — user-generated data | `estimates`, `line_items`, `users` |
| `sync_` | Lakebase | Tables synced (CDC) from Unity Catalog, or loaded from the bundled snapshot; **authoritative for the app at runtime** | `sync_pricing_dbu_rates` |
| `sync_ref_` | Lakebase | Synced *reference* data (lookup dimensions) | `sync_ref_instance_dbu_rates` |
| `sync_product_` | Lakebase | Synced *product rate* data (serverless/LLM products) | `sync_product_fmapi_databricks` |
| `ref_` | Lakebase | Static reference data seeded by the installer (not synced) | `ref_workload_types`, `ref_cloud_tiers` |
| `lakemeter.<fn>` | Lakebase | SQL functions, grouped by file number `01–09` | `lakemeter.get_dbu_price` |
| `lakemeter_catalog.lakemeter.*` | UC | Raw pricing tables, source of record | `dbu_prices`, `vm_costs` |

Rules that follow from this:

1. **The app only reads `sync_*` / `ref_*` pricing tables and writes only app
   tables.** It never reads Unity Catalog directly.
2. **`sync_*` tables are replaceable.** Any refresh may `TRUNCATE` and reload them.
   Never store user data in a `sync_*` table; never add a foreign key from an app
   table to a `sync_*` table (a reload would break it).
3. **App tables are never truncated by any pipeline.** Pricing refreshes touch only
   `sync_*` / `ref_*`.
4. **Enum-like values have canonical case**, enforced by triggers (§3.4): clouds,
   tiers, workload types, warehouse types, DLT editions are UPPER; mode/provider/
   rate-type fields are lower.

---

## 2. Unity Catalog layer

### 2.1 Structure

```
lakemeter_catalog                    ← catalog (created once per workspace)
└── lakemeter                        ← schema
    ├── dbu_prices                   ← from 01_Fetch_DBU_Prices
    ├── sku_region_mapping           ← from 01_Fetch_DBU_Prices
    ├── instance_rates               ← from 02_Load_DBU_Rates (Excel)
    ├── vm_costs                     ← from 03/04/05_Fetch_*_VM
    ├── dbsql_rates                  ← from 07_Load_DBSQL_Rates
    ├── dbu_multipliers              ← from 09_Load_DBU_Multipliers
    ├── serverless_product_rates     ← from 10_Load_Serverless_Product_Rates
    ├── fmapi_databricks_rates       ← from 11_Load_FMAPI_Databricks_Rates
    └── fmapi_proprietary_rates      ← from 12_Load_FMAPI_Proprietary_Rates
```

Setup:

```sql
CREATE CATALOG IF NOT EXISTS lakemeter_catalog;
CREATE SCHEMA IF NOT EXISTS lakemeter_catalog.lakemeter;
```

### 2.2 Core pricing tables

**`dbu_prices`** — Databricks list price per SKU. Grain: one row per
`cloud, region, tier, product_type, sku_name`. Primary key is that five-column
composite. Sourced from `system.billing.list_prices`. Key columns:

| Column | Type | Notes |
|---|---|---|
| `cloud` | string | `aws` / `azure` / `gcp` (lowercase in UC; upper-cased on the Lakebase side) |
| `region` | string | Cloud region code, e.g. `us-east-1`, `eastus`, `us-central1` |
| `tier` | string | `STANDARD` / `PREMIUM` / `ENTERPRISE` |
| `product_type` | string | Canonical SKU family, e.g. `JOBS_COMPUTE`, `ALL_PURPOSE_COMPUTE_(PHOTON)`, `SERVERLESS_SQL_COMPUTE` |
| `sku_name` | string | As-reported SKU name from the price list |
| `price` | decimal | USD per DBU (or per unit for non-DBU SKUs) |

**`vm_costs`** — Cloud VM hourly prices. Grain: one row per
`cloud, region, instance_type, pricing_tier, payment_option`.
`pricing_tier` is `on_demand` / `reserved` / `spot`; `payment_option` is `NA` for
on-demand and the reservation term otherwise. Roughly 111k rows across the three
clouds in the current snapshot.

**`instance_rates`** — DBU-per-hour consumed by each instance type. Grain:
`cloud, instance_type`. Sourced from the maintained `Instance Type Pricing.xlsx`
(the cloud price lists don't publish DBU consumption; this file does).

**`sku_region_mapping`** — Maps SKU-region names as they appear in price lists to
canonical region codes (`cloud, sku_region` → `region`).

### 2.3 Product and reference tables

| Table | Grain | Contents |
|---|---|---|
| `dbsql_rates` | warehouse type × size | DBU/hour for classic/pro/serverless warehouses |
| `serverless_product_rates` | cloud × product | Vector Search and Model Serving unit rates |
| `fmapi_databricks_rates` | model × endpoint type × context | Token rates for Databricks-hosted models |
| `fmapi_proprietary_rates` | provider × model × rate type | Token rates for external models (OpenAI, Anthropic, Google…) |
| `dbu_multipliers` | multiplier kind | Photon and related uplift factors |
| `dbsql_warehouse_config` | warehouse size | Instance configuration behind each T-shirt size |

### 2.4 Governance (UC)

- **Owner:** a service principal or dedicated group, not an individual user. The
  fetch notebooks run as that identity.
- **Grants:** `USAGE` on catalog+schema and `SELECT` on all tables to the Lakebase
  sync identity; `MODIFY` only to the refresh identity. No broad `ALL PRIVILEGES`.
- **Refresh cadence:** DBU prices and VM costs monthly (after vendor price updates);
  instance rates quarterly; FMAPI rates on model-release events (see Issue #20 for
  the 2026-10-16 Gemini retirement).
- **Quality gates:** run `99_Debug_Data_Quality.ipynb` after every refresh — it
  checks duplicate keys, missing regions, and DBU-price/VM-cost coverage mismatches.
  The SQL checks are documented in `etl/pricing_sync/README.md`.
- **Volumes:** the pipeline currently uses tables only. If raw vendor price-list
  dumps are ever retained for audit, store them in a UC **Volume**
  `lakemeter_catalog.lakemeter.pricing_raw` with the same owner/grants, one
  subfolder per fetch date (`yyyy-mm-dd/`), and a 90-day retention convention.

---

## 3. Lakebase layer

- **Instance:** Lakebase Autoscaling, provisioned by `01_provision_lakebase.py`.
- **Database:** `lakemeter_pricing`.
- **Schema:** `lakemeter`.
- **Roles:** the installing identity owns everything; `lakemeter_sync_role` is a
  password-login fallback role (see §5 and Issue #19) granted full DML on the schema;
  the app's service principal connects via OAuth tokens.

### 3.1 Application tables

**`users`** — one row per person who has opened the app.

| Column | Type | Notes |
|---|---|---|
| `user_id` | UUID PK | generated by the backend |
| `email` | VARCHAR(255) UNIQUE NOT NULL | from Databricks SSO headers; the natural identity |
| `full_name` | VARCHAR(255) | display name |
| `role` | VARCHAR(50) | app-level role (e.g. admin) |
| `is_active` | BOOLEAN DEFAULT true | soft deactivation |
| `last_login_at` | TIMESTAMP | updated on each authenticated request |
| `created_at` / `updated_at` | TIMESTAMP DEFAULT CURRENT_TIMESTAMP | audit |

**`estimates`** — the top-level document a user edits.

| Column | Type | Notes |
|---|---|---|
| `estimate_id` | UUID PK | |
| `estimate_name` | VARCHAR(500) | |
| `owner_user_id` | UUID FK → users | the creator; sharing (below) grants others access |
| `sfdc_account_id`, `customer_name`, `uco_id`, `opportunity_id` | VARCHAR | optional CRM linkage |
| `cloud`, `region`, `tier` | VARCHAR | defaults inherited by new line items; `cloud`/`tier` upper-cased by trigger |
| `status` | VARCHAR(20) DEFAULT 'draft' | draft / final etc. |
| `version` | INT DEFAULT 1 | optimistic versioning |
| `template_id` | UUID FK → templates | origin template, if any |
| `original_prompt` | TEXT | the AI-assistant prompt that started the estimate, if any |
| `display_order` | INT DEFAULT 0 | UI ordering |
| `is_deleted` | BOOLEAN DEFAULT false | soft delete — rows are never hard-deleted by the app |
| `discount_config` | JSONB | per-estimate discount rules |
| `created_at` / `updated_at` / `updated_by` | audit | `updated_by` FK → users |

**`line_items`** — one row per workload inside an estimate; the heart of the system.
~80 columns by design (ADR: one wide table; `workload_config` JSON is the overflow).
Key groups:

| Group | Columns |
|---|---|
| Identity | `line_item_id` UUID PK, `estimate_id` UUID FK → estimates, `display_order`, `workload_name`, `workload_type` VARCHAR(50) NOT NULL (FK to `ref_workload_types` by convention) |
| Context | `cloud`, `serverless_enabled`, `serverless_mode`, `photon_enabled` |
| Classic compute | `driver_node_type`, `worker_node_type`, `num_workers`, `driver_pricing_tier`, `worker_pricing_tier`, `driver_payment_option`, `worker_payment_option` |
| DLT | `dlt_edition` |
| DBSQL | `dbsql_warehouse_type`, `dbsql_warehouse_size`, `dbsql_num_clusters`, `dbsql_vm_pricing_tier`, `dbsql_vm_payment_option` |
| Vector Search | `vector_search_mode`, `vector_capacity_millions`, `vector_search_storage_gb` |
| Model Serving | `model_serving_gpu_type`, `model_serving_concurrency`, `model_serving_scale_out`, `model_servings_number_endpoints` |
| FMAPI | `fmapi_provider`, `fmapi_model`, `fmapi_endpoint_type`, `fmapi_context_length`, `fmapi_rate_type`, `fmapi_quantity` BIGINT |
| Databricks Apps | `databricks_apps_size`, `databricks_apps_hours_per_month`, `databricks_apps_num_apps` |
| AI Parse | `ai_parse_calculation_method`, `ai_parse_mode`, `ai_parse_complexity`, `ai_parse_dbu_quantity`, `ai_parse_num_pages`, `ai_parse_pages_thousands` |
| Shutterstock | `shutterstock_imageai_num_images`, `shutterstock_images` |
| Support | `databricks_support_tier`, `databricks_support_annual_commit` |
| Lakeflow Connect | `lakeflow_connect_*` (connector type, pipeline node types/workers/runs/runtime/hours, gateway cloud/instance/workers/hours, modes, enabled flag) |
| Lakebase | `lakebase_cu` NUMERIC(5,1) with `CHECK (lakebase_cu IN (0.5, 1, 2, …, 112))`, `lakebase_storage_gb`, `lakebase_ha_nodes`, `lakebase_backup_retention_days`, `lakebase_pitr_gb`, `lakebase_snapshot_gb` |
| Usage | `runs_per_day`, `avg_runtime_minutes`, `days_per_month` DEFAULT 30, `hours_per_month` DECIMAL(10,2) |
| Overflow / results | `workload_config` JSON, `notes` TEXT, `cost_calculation_response` JSON (the stored breakdown), `calculation_completed_at` |
| Audit | `created_at`, `updated_at` |

Indexes: `idx_line_items_estimate (estimate_id)`, `idx_line_items_workload_type (workload_type)`.

**`conversation_messages`** — AI assistant history per estimate:
`message_id` UUID PK, `estimate_id` FK, `message_role`, `message_content`,
`message_sequence`, `message_type`, `tokens_used`, `model_used`, `created_at`.

**`decision_records`** — assistant reasoning audit trail:
`record_id` UUID PK, `line_item_id` FK, `record_type`, `user_input`,
`agent_response`, `assumptions` JSON, `calculations` JSON, `reasoning`, `created_at`.

**`sharing`** — estimate sharing:
`share_id` UUID PK, `estimate_id` FK, `share_type`, `shared_with_user_id` FK → users,
`share_link` VARCHAR(255) UNIQUE, `permission`, `expires_at`, `access_count`,
`last_accessed_at`, `created_at`.

**`templates`** — estimate templates: `template_id` UUID PK, `template_name`,
`workload_type`, `file_path`, `file_format`, `mandatory_fields`/`optional_fields` JSON,
`description`, `version`, `is_active`, audit columns.

### 3.2 Seeded reference tables

**`ref_workload_types`** — the workload catalog *and* the UI form contract. PK
`workload_type`. Columns include `display_name`, `description`, fifteen
`show_*` BOOLEAN flags (`show_compute_config`, `show_serverless_toggle`,
`show_serverless_performance_mode`, `show_photon_toggle`, `show_dlt_config`,
`show_dbsql_config`, `show_serverless_product`, `show_fmapi_config`,
`show_lakebase_config`, `show_vector_search_mode`, `show_vm_pricing`,
`show_usage_hours`, `show_usage_runs`, `show_usage_tokens`), the three SKU product
types (`sku_product_type_standard`, `sku_product_type_photon`,
`sku_product_type_serverless`), and `display_order`. Nine rows are seeded at install
(JOBS, ALL_PURPOSE, DLT, DBSQL, VECTOR_SEARCH, MODEL_SERVING, FMAPI_DATABRICKS,
FMAPI_PROPRIETARY, LAKEBASE); the remaining workload types are added by later
migrations/seeds. Inserts use `ON CONFLICT DO NOTHING` — re-running is safe.

**`ref_cloud_tiers`** — PK `(cloud, tier)`; eight seeded rows (AWS/GCP:
STANDARD, PREMIUM, ENTERPRISE; Azure: STANDARD, PREMIUM).

### 3.3 Synced pricing tables (`sync_*`)

Loaded by `03_load_pricing_data.py` from the bundled snapshot, or synced from UC.
All are reloaded with `TRUNCATE` + bulk insert and may be recreated with
`CREATE TABLE IF NOT EXISTS`. The loader asserts the expected CSVs exist before
starting, so a partial load is impossible.

| Table | Loaded from | Notes |
|---|---|---|
| `sync_pricing_dbu_rates` | `dbu-rates.csv` | mirrors UC `dbu_prices`; readiness endpoint checks this table is populated |
| `sync_pricing_vm_costs` | `vm-costs.csv` (+ `_partN` splits) | mirrors UC `vm_costs`; also checked by readiness |
| `sync_product_dbsql_rates` | `dbsql-rates.csv` | |
| `sync_product_serverless_rates` | `serverless-rates.csv` | |
| `sync_product_fmapi_databricks` | `fmapi-databricks-rates.csv` | |
| `sync_product_fmapi_proprietary` | `fmapi-proprietary-rates.csv` | |
| `sync_ref_instance_dbu_rates` | `instance-dbu-rates.csv` | |
| `sync_ref_dbu_multipliers` | `dbu-multipliers.csv` | |
| `sync_ref_dbsql_warehouse_config` | `dbsql-warehouse-config.csv` | |
| `sync_ref_sku_region_map` | `sku-region-map.csv` | |

Plus small curated lookups created by the same notebook: `ref_fmapi_databricks_models`,
`ref_fmapi_proprietary_models`, `ref_model_serving_gpu_types`.

### 3.4 Triggers (case normalization)

Two `BEFORE INSERT OR UPDATE` triggers (defined in `02_create_database.py`):

- `trg_normalize_estimates_case` on `estimates` → `normalize_estimates_case()`:
  upper-cases `cloud`, `tier`.
- `trg_normalize_line_items_case` on `line_items` → `normalize_line_items_case()`:
  upper-cases `cloud`, `workload_type`, `dbsql_warehouse_type`, `dlt_edition`;
  lower-cases `serverless_mode`, `vector_search_mode`, `fmapi_provider`,
  `fmapi_rate_type`, `fmapi_endpoint_type`, `fmapi_context_length`,
  `model_serving_gpu_type`, `driver_pricing_tier`, `worker_pricing_tier`.

**When you add an enum-like column, add it to the trigger in the same change**, and
keep pricing join keys consistent with this casing.

### 3.5 SQL functions (calculation engine)

Deployed by `02b_create_functions.py` from `scripts/functions/01–09`. All live in
schema `lakemeter`; all are `CREATE OR REPLACE`, so redeploying updates them in place.

| Function | Defined in | Purpose |
|---|---|---|
| `calculate_hours_per_month` | 01 | Converts runs/day × runtime, or hours/month inputs, into billable hours |
| `get_product_type_for_pricing` | 01 | Resolves the canonical SKU product type for a workload (tries `sku_name`, then legacy `product_type`) |
| `get_dbu_price` | 01 | Looks up USD/DBU in `sync_pricing_dbu_rates` for cloud/region/tier/product |
| `get_photon_multiplier` | 01 | Photon uplift factor from `sync_ref_dbu_multipliers` |
| `calculate_classic_compute_dbu` | 02 | DBUs for Jobs / All-Purpose / DLT classic clusters |
| `calculate_serverless_compute_dbu` | 03 | DBUs for serverless Jobs / All-Purpose / DLT |
| `calculate_dbsql_dbu` | 04 | Warehouse DBUs across classic / pro / serverless |
| `calculate_vector_search_dbu` | 05 | Vector Search endpoint cost |
| `calculate_model_serving_dbu` | 05 | Model Serving endpoint cost |
| `calculate_fmapi_databricks_dbu` | 06 | Token cost for Databricks-hosted models |
| `calculate_fmapi_proprietary_dbu` | 06 | Token cost for external models |
| `calculate_classic_vm_costs` | 08 | Driver+worker VM cost for classic compute |
| `calculate_dbsql_vm_costs` | 08 | VM cost behind classic DBSQL warehouses |
| `calculate_line_item_costs` | 09 | **Orchestrator**: given a line item, dispatches to the right calculators and returns the full breakdown JSON that gets stored in `line_items.cost_calculation_response` |

File numbers `01–09` are significant and gaps are intentional (there is no `07`).
Add new calculators in the matching numbered file, register them in the orchestrator,
and add a test notebook under `etl/lakebase_setup/tests/`.

---

## 4. Migration and evolution rules

1. **Additive-only by default.** New columns via `ADD COLUMN IF NOT EXISTS` in
   `02_create_database.py`'s `migration_columns` list; new tables via
   `CREATE TABLE IF NOT EXISTS`; function changes via `CREATE OR REPLACE`.
2. **Every installer step is idempotent** — re-running the installer is the upgrade
   path. Seeds use `ON CONFLICT DO NOTHING`.
3. **Destructive changes** (drops, renames, type narrowing) are exceptional and ship
   as numbered release scripts under `etl/lakebase_setup/release_N/` with a README
   and a validation step (see `release_2/` for the pattern).
4. **Constraints with business meaning** (like the `lakebase_cu` allowed-values
   check) live in the database, not only in the app, so notebook users get the same
   guarantees.

---

## 5. Access and governance summary

| Identity | UC `lakemeter_catalog.lakemeter` | Lakebase `lakemeter` schema |
|---|---|---|
| Pricing-refresh identity (SP/group) | OWNER / `MODIFY` + `SELECT` | DDL + DML (loads `sync_*`) |
| App service principal | none | DML on app tables; `SELECT` + `EXECUTE` on pricing tables/functions (OAuth token auth) |
| `lakemeter_sync_role` (fallback) | none | full DML, password auth (see Issue #19 — new projects disable password auth by default) |
| Analysts (SQL editor/notebooks) | `SELECT` | `SELECT` + `EXECUTE` as granted |
| End users | none | none directly — they go through the app, which enforces ownership/sharing |

Credentials live in a Databricks secrets scope (`lakebase-user`,
`lakebase-password`, `lakebase-host`, `lakebase-database`) created by the installer;
nothing secret is ever committed to the repo. TLS is required (`DB_SSLMODE=require`).
