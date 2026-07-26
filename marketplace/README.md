# Lakemeter — Databricks Marketplace Listing

Draft collateral for listing Lakemeter on Databricks Marketplace (Apps
category, Public Preview as of June 2026). Listing requires onboarding
as a Marketplace provider through the Databricks Data Partner Program —
this directory contains everything needed to complete the listing form
and pass the app security review.

## Provider profile (fill in at onboarding)

| Field | Value |
|---|---|
| Provider name | *<your organization>* |
| Description | Databricks-native cost estimation and pricing tools |
| Organization website | *<url>* |
| Support email | *<email>* |
| Terms of service link | *<url>* |
| Privacy policy link | *<url>* |

## Listing draft

**Name:** Lakemeter — Databricks Pricing Calculator

**Tagline:** Estimate Databricks workload costs across Jobs, DBSQL,
DLT, Model Serving, FMAPI, Vector Search, and Lakebase — entirely
inside your workspace.

**Description:**

Lakemeter is a Databricks-native pricing calculator that runs 100%
inside the customer's workspace. It estimates monthly costs for every
Databricks workload type, from serverless and classic compute to
Foundation Model APIs and Lakebase OLTP, using pricing data loaded
into the customer's own Lakebase database — no data ever leaves the
workspace.

- **Nine workload types:** Jobs, All-Purpose, DLT (Lakeflow), DBSQL,
  Vector Search, Model Serving, FMAPI (Databricks-hosted and
  proprietary models), Lakebase
- **Multi-cloud pricing:** AWS, Azure, and GCP rate data across 70+
  regions, refreshed with every release
- **Accurate by construction:** cost math runs in PostgreSQL stored
  functions backed by pricing tables in the customer's Lakebase
  instance; an AI assistant (Claude via Foundation Model APIs) helps
  build estimates conversationally
- **Excel export** with full cost breakdowns, SKU detail, and
  documented assumptions for procurement workflows
- **Estimate management:** save, version, share, and template estimates
  with workspace-user access control

**Categories:** Analytics, Cost Management / FinOps

**Keywords:** pricing, cost estimation, finops, tco, calculator

## Resource and scope declarations (from `app.yaml`)

| Resource | Type | Purpose |
|---|---|---|
| `lm-lakebase-instance` | Secret | Lakebase instance name |
| `lm-db-host` | Secret | Lakebase endpoint |
| `lm-db-user` | Secret | Database role |
| `lm-db-name` | Secret | Database name |
| `lm-claude-endpoint` | Serving endpoint (`CAN_QUERY`) | AI assistant inference |

All secrets bind to the consumer-owned `lakemeter-secrets` scope at
install; the app authenticates to Lakebase via its Service Principal
(OAuth M2M with automatic token refresh).

## Egress declaration

Lakemeter makes **no external network calls at runtime**. All pricing
data ships in the app bundle and in Lakebase tables; AI inference goes
to the workspace's own Foundation Model API endpoints. Package
registries (`pypi.org`, `files.pythonhosted.org`, `registry.npmjs.org`)
are needed at deploy/build time only.

## Readiness checklist (partner architecture guide)

| Requirement | Status |
|---|---|
| Supported framework (Python FastAPI + React) | ✅ |
| `readme.md` for the listing | ✅ this file + repo README |
| No PATs in code or config | ✅ (OAuth M2M + secrets only) |
| Minimal, documented scopes | ✅ 5 bindings, table above |
| External domains declared | ✅ none at runtime (see above) |
| Resources declared in `app.yaml`, none hardcoded | ✅ |
| Secrets bind to consumer-owned scopes | ✅ |
| Native services preferred (Lakebase, FMAPI) | ✅ Lakebase + Claude FMAPI |
| Dependency manifests present | ✅ `requirements.txt`, `package.json` + lockfiles |
| Dependencies pinned | ⚠️ manifests use `>=` ranges — consider lockfile pins before submission |
| `SECURITY.md` with reporting path | ✅ PR #17 |
| Static analysis / tests in CI | ✅ PR #4 (`ci.yml`) |
| Git-based deploy + tagged releases | ✅ PR #6 (DABs) + PR #14 (tag-driven releases) |
| SBOM available | ✅ PR #17 (`security.yml`) |
| Structured logs | ✅ PR #18 (`LOG_FORMAT=json`) |
| Health/status endpoint for consumers | ✅ PR #18 (`/health`, `/health/ready`) |
| Vulnerability tracking | ✅ Issues #19, #20 |
| Two-person review on Marketplace-bound changes | ⚠️ process — enable branch protection requiring 1 approval |
| Tested against SEG-restricted workspace | ⚠️ manual pre-submission step |
| Consumer install walked in a clean workspace | ⚠️ manual pre-submission step |

## Submission steps (once provider-approved)

1. Confirm the two ⚠️ process items above
2. Cut a release (`vX.Y.Z` tag → GitHub Release via `release.yml`)
3. Submit the app pinned to the release tag for Marketplace security
   review
4. Create the listing from this document's draft content
