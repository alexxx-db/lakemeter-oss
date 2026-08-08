---
sidebar_position: 2
---

# Installer Guide

Lakemeter includes a one-command installer (`scripts/install.sh`) that provisions a complete environment on Databricks — from Lakebase instance creation to app deployment and verification. All heavy lifting runs on Databricks serverless compute via a DABs (Databricks Asset Bundles) workflow. Total installation time is approximately **15-20 minutes**.

## Prerequisites

### Local machine

- **Databricks CLI** installed and configured with a workspace profile ([installation guide](https://docs.databricks.com/en/dev-tools/cli/install.html))
  - DABs support is included in the CLI (no additional installation needed)
  - Verify with: `databricks --version` (requires 0.200+)

That's it — no Python packages, no Node.js, no other dependencies needed locally.

### Databricks workspace

- **AWS** or **Azure** workspace in a [Lakebase-supported region](https://docs.databricks.com/en/oltp/projects/manage-projects.html):
  - **AWS:** `us-east-1`, `us-east-2`, `us-west-2`, `ca-central-1`, `sa-east-1`, `eu-central-1`, `eu-west-1`, `eu-west-2`, `ap-south-1`, `ap-southeast-1`, `ap-southeast-2`
  - **Azure:** `eastus`, `eastus2`, `centralus`, `southcentralus`, `westus`, `westus2`, `canadacentral`, `brazilsouth`, `northeurope`, `uksouth`, `westeurope`, `australiaeast`, `centralindia`, `southeastasia`

All required permissions (Lakebase, secret scopes, Apps, serverless compute) are granted to all workspace users by default. No special admin setup is needed.

The installer handles everything else automatically:
- Lakebase instance provisioning (reuses existing if same name)
- Database creation, schema setup, and stored functions
- Pricing data loading from pre-flattened CSV files included in the repository
- App Service Principal creation and Lakebase access grants
- App deployment and smoke test verification

## Usage

```bash
# Clone the repository
git clone https://github.com/databrickslabs/lakemeter-oss.git
cd lakemeter-oss

# Interactive installation (prompts for names)
./scripts/install.sh --profile <cli-profile>

# Non-interactive (use all defaults)
./scripts/install.sh --profile <cli-profile> --non-interactive
```

### CLI Flags

| Flag | Description |
|------|-------------|
| `--profile` | Databricks CLI profile name (required if not using DEFAULT) |
| `--non-interactive` | Use all defaults with no prompts (for CI/CD pipelines) |
| `--instance-name` | Lakebase instance name (default: `lakemeter-customer`) |
| `--db-name` | Database name (default: `lakemeter_pricing`) |
| `--app-name` | App name (default: `lakemeter`) |
| `--secrets-scope` | Secret scope name (default: `lakemeter-secrets`) |
| `-h`, `--help` | Show usage help |

## What You'll See

### Phase 1: Configuration

The installer checks connectivity and prompts for configuration (or uses defaults in `--non-interactive` mode):

```
Lakemeter Installer
================================

Checking workspace connectivity...
Connected as: admin@company.com

Configuration (press Enter to accept defaults)

  Lakebase instance name [lakemeter-customer]:
  Database name [lakemeter_pricing]:
  App name [lakemeter]:
  Secrets scope [lakemeter-secrets]:

Configuration:
  Instance name:  lakemeter-customer
  Database:       lakemeter_pricing
  App name:       lakemeter
  Secrets scope:  lakemeter-secrets
  Claude endpoint: databricks-claude-opus-4-6
```

### Phase 2: Bundle Deploy

Uploads notebooks, pricing data, and app source to the workspace:

```
Preparing bundle...
  Splitting vm-costs.csv (12MB)...
  Split into 2 parts
  Pricing data: 11 CSV files
  App source prepared

Deploying bundle to workspace...
Uploading bundle files to /Workspace/Users/admin@company.com/.bundle/lakemeter-installer/default/files...
Deploying resources...
Updating deployment state...
Deployment complete!
Bundle deployed
```

### Phase 3: Workflow Execution (~15 minutes)

The installer launches a DABs workflow with 9 tasks and shows live progress:

```
Running installer workflow on serverless compute...
  This will provision Lakebase, create tables, load pricing data,
  configure the app, and deploy it.

Note: The full installation typically takes 15-20 minutes.

  Run URL: https://your-workspace.cloud.databricks.com/#job/.../run/...

  Task Progress:
    [done] provision_lakebase
    [done] create_app
    [done] create_database
    [done] create_functions
    [done] load_pricing_data
    [done] create_sku_mapping
    [done] grant_app_access
    [ .. ] deploy_app             running
    [    ] verify_installation    waiting
  Elapsed: 12m31s
```

The progress display refreshes every 10 seconds with live task status:
- `[done]` — completed
- `[ .. ]` — currently running
- `[    ]` — waiting for dependencies
- `[FAIL]` — task failed (installer exits with error details)

### Phase 4: Completion

```
Installation complete!

  App URL:      https://lakemeter-<workspace-id>.<cloud>.databricksapps.com
  Verification: All smoke tests passed
  Details:      databricks runs get-output --run-id XXXXX --profile <profile>
```

## The 9-Task Workflow

The DABs workflow executes 9 notebook tasks with parallelization where possible:

```
provision_lakebase  ║  create_app           ← run in parallel
      │             ║        │
create_database     ║        │
      │             ╠════════╝
  ┌───┴──────┐      │
funcs      data   grant_app_access
            │           │
         sku_map   deploy_app
                        │
                   verify_installation
```

| Task | Description |
|------|-------------|
| **provision_lakebase** | Creates or reuses a Lakebase instance with autoscaling and scale-to-zero |
| **create_app** | Creates the Databricks App and configures secret references (runs in parallel with provisioning) |
| **create_database** | Creates the database, schema, tables, reference data, and auth roles |
| **create_functions** | Deploys 19 stored functions for cost calculations |
| **load_pricing_data** | Bulk-loads pricing reference data from CSV files |
| **create_sku_mapping** | Populates SKU discount mapping table |
| **grant_app_access** | Grants the app's Service Principal access to Lakebase |
| **deploy_app** | Uploads app source and deploys (this is the longest step — mostly Databricks Apps infrastructure time) |
| **verify_installation** | Runs ~80 smoke tests covering all APIs, reference data, cost calculations, AI assistant, and Excel export |

## Configuration

| Parameter | Default | Description |
|-----------|---------|-------------|
| Instance name | `lakemeter-customer` | Lakebase instance identifier |
| Database name | `lakemeter_pricing` | PostgreSQL database name |
| App name | `lakemeter` | Databricks App name |
| Secrets scope | `lakemeter-secrets` | Databricks secret scope name |

The following are fixed (not user-configurable):

| Setting | Value | Reason |
|---------|-------|--------|
| Lakebase scaling | 1–16 CU, scale-to-zero | Optimal for cost and performance |
| Claude endpoint | `databricks-claude-opus-4-6` | Same endpoint on every Databricks workspace |
| Serverless environment | v5 | Latest serverless environment version |

## What Gets Created

After a successful installation, your workspace will have:

| Resource | Details |
|----------|---------|
| **Lakebase instance** | `lakemeter-customer` — 1-16 CU, scale-to-zero |
| **Database** | `lakemeter_pricing` with `lakemeter` schema |
| **Secret scope** | `lakemeter-secrets` with 5 secrets |
| **Databricks App** | `lakemeter` with 5 resources |
| **App URL** | `https://lakemeter-<workspace-id>.<cloud>.databricksapps.com` |

For a detailed breakdown of all resources created, see the [Deployment Inventory](./deployment-inventory).

## Re-running the Installer

The installer is **idempotent** — running it again on the same workspace will:

- Reuse the existing Lakebase instance (no data loss)
- Reuse the existing app (no downtime during reconfiguration)
- Re-create tables with `IF NOT EXISTS` (existing data preserved)
- Reload pricing data via `TRUNCATE + INSERT` (refreshes to latest)
- Re-grant SP access (harmless if already granted)
- Redeploy the app (picks up code changes)

This means you can safely re-run the installer to:
- Update pricing data after a new release
- Fix a broken deployment
- Add newly created stored functions

## Scheduled Pricing Sync

The installer bundle also deploys a **Lakemeter Pricing Sync** job — a
monthly refresh (06:00 UTC on the 1st) that reloads the pricing CSV
snapshot shipped with your installed version into the Lakebase `sync_*`
tables, using the same idempotent `TRUNCATE + INSERT` load as the
installer itself.

The schedule is deployed **paused** by default. Enable it either at
deploy time:

```bash
databricks bundle deploy --var="pricing_sync_pause_status=UNPAUSED"
```

or afterwards in the **Workflows** UI (unpause the job schedule).

How this fits the release cadence:

1. A new Lakemeter release ships refreshed pricing data (patch releases
   include pricing updates — see [Releasing](https://github.com/alexxx-db/lakemeter-oss/blob/main/RELEASING.md)).
2. You deploy the new version (re-run the installer or the day-2 bundle).
3. The next scheduled run — or a manual **Run now** — refreshes the
   Lakebase tables to match, with no app downtime.

If you prefer to control refresh timing yourself, leave the schedule
paused and re-run the installer after each upgrade instead.

## Actuals Usage Sync

The bundle also deploys a **Lakemeter Actuals Sync** job: a daily ingest
(04:00 UTC) that reads `system.billing.usage` (joined to
`system.billing.list_prices` for list prices) and appends daily-grain
consumption records into the Lakebase table
`lakemeter.actuals_usage_daily`. This is the raw material for actual-cost
reporting and per-user attribution; the estimate side of the app does not
depend on it.

Key properties:

- **Incremental**: a watermark table (`lakemeter.actuals_ingestion_state`)
  tracks progress; each run reprocesses a trailing 7-day window via
  DELETE + INSERT, so late-arriving billing records are picked up
  automatically and re-running the job never duplicates rows.
- **Correction-safe**: billing correction records (negative quantities,
  for example Genie One/Agents usage negated while free through
  2027-01-31) are loaded as-is so sums stay correct.
- **Attribution-ready**: each row carries `run_as`, `owned_by`,
  `created_by`, asset identifiers (warehouse, serving endpoint, cluster,
  job, pipeline), and `custom_tags`.
- **Data-quality checked**: rows with no matching list price are kept
  (with NULL price) and counted at the end of each run; a warning prints
  if unpriced rows exceed 20%.

Permissions: the identity running the job needs read access to
`system.billing.usage` and `system.billing.list_prices` (account admin, or
a principal granted `USE CATALOG` and `SELECT` on the `system` catalog).

The schedule is deployed **paused** by default. Enable it at deploy time:

```bash
databricks bundle deploy --var="actuals_sync_pause_status=UNPAUSED"
```

or unpause the schedule in the **Workflows** UI, or run it once manually
with **Run now**. The first run backfills the last 30 days; you can widen
that with the `initial_backfill_days` notebook parameter.
