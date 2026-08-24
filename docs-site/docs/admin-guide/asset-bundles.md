---
sidebar_position: 6
---

# Deploying with Asset Bundles

Lakemeter uses **two** Databricks Asset Bundles, one per lifecycle stage:

| Bundle | Location | Purpose |
|---|---|---|
| Installer | `scripts/databricks.yml` | One-time provisioning: Lakebase instance, database, schema + functions, pricing data, secrets, app creation (runs as a serverless job). |
| App deployment | `databricks.yml` (repo root) | Day-2 updates: sync app source, configure app resources, deploy the app. |

This page covers the **root bundle** — the fast path for shipping code updates after the initial install. The installer bundle is covered by the [Installer Guide](./installer).

## Prerequisites

- Databricks CLI **0.261+** (apps-in-bundles support). Verify with `databricks version`.
- The installer has been run at least once — the bundle expects the secret scope (`lakemeter-secrets`) and the Claude serving endpoint to exist.
- A built frontend: run `./deploy.sh` (no flags) once to regenerate `backend/static/`.

## Quick start

```bash
./deploy.sh                          # 1. build the frontend into backend/static/
databricks bundle validate           # 2. check config (dev target by default)
databricks bundle deploy             # 3. sync source to workspace + configure app
databricks bundle run lakemeter      # 4. deploy the app
```

That's it — the bundle replaces the manual `databricks workspace import-dir ...` + `databricks apps deploy` sequence in `deploy.sh --workspace-deploy`.

## Targets

Two targets are defined:

```bash
databricks bundle deploy             # dev (default)  → app 'lakemeter-dev'
databricks bundle deploy -t prod     # prod           → app 'lakemeter'
```

- **dev** runs in bundle development mode: resource names are prefixed with `[dev <user>]`-style tags and deployment metadata is marked as development — safe for iteration alongside the production app.
- **prod** runs in production mode and deploys the app as `lakemeter`.

Both targets read authentication from your active CLI profile or the standard
`DATABRICKS_HOST` / `DATABRICKS_TOKEN` / `DATABRICKS_CLIENT_ID` / `DATABRICKS_CLIENT_SECRET`
environment variables.

## What gets synced

Only runtime files, mirroring the deploy.sh parallel-sync set:

- `backend/app/**` (Python source, minus `__pycache__`)
- `backend/static/**` (pre-built frontend + JSON pricing bundle, **minus CSVs** — pricing data lives in Lakebase)
- `app.yaml`, `requirements.txt`

Everything else (`frontend/`, `etl/`, `tests/`, `docs-site/`) stays out of the workspace.

## App resources

The bundle declares the app resources that back the `valueFrom` entries in
`app.yaml` — four secrets (Lakebase instance name, host, user, database) from
the `lakemeter-secrets` scope, plus the Claude serving endpoint with
`CAN_QUERY` permission.

:::warning Keep names in sync
The resource names in `databricks.yml` (`lakemeter-db-host`, etc.) must match
the `valueFrom` names in `app.yaml` exactly. They are app-scoped, so the same
names work for every target — but if you rename one side, rename the other in
the same commit.
:::

## Variables

| Variable | Default | Purpose |
|---|---|---|
| `app_name` | `lakemeter` | Databricks App name |
| `secrets_scope` | `lakemeter-secrets` | Secret scope with Lakebase config |
| `claude_endpoint` | `databricks-claude-opus-4-6` | Model endpoint for the AI Assistant |

Override per deploy, e.g.:

```bash
databricks bundle deploy --var="claude_endpoint=databricks-claude-sonnet-4"
```

## CI/CD

A reference GitHub Actions workflow (`bundle` — see the PR that introduced this
file or your fork's `.github/workflows/bundle.yml`) does the following:

- **On every PR**: builds the frontend, installs the Databricks CLI, and runs
  `databricks bundle validate` against both targets.
- **On manual dispatch** (`workflow_dispatch`, target input): runs
  `databricks bundle deploy` + `databricks bundle run lakemeter` against the
  chosen target.

Required secrets: `DATABRICKS_HOST`, `DATABRICKS_CLIENT_ID`,
`DATABRICKS_CLIENT_SECRET` (use a service principal that owns the app).
