---
sidebar_position: 99
---

# Changelog

Lakemeter follows [Semantic Versioning](https://semver.org/):

- **Major** (X.0.0) — Schema migrations and breaking database changes
- **Minor** (0.X.0) — Data-only database updates
- **Patch** (0.0.X) — Application-only fixes with no database changes

---

## Unreleased

Security, trust, and platform hardening on top of v0.1.1:

- Locked down user APIs and bound AI chat conversations to SSO ownership
- Removed unused production JWT gate (Apps SSO identity headers only)
- Least-privilege Lakebase grants for App SP and password fallback role
- Pricing freshness metadata + paused weekly refresh job + UI “prices as of”
- Durable AI conversation persistence in Lakebase (`ai_conversations`)
- Installer DAB targets (`dev`/`staging`/`prod`) with job/task timeouts
- Expanded CI with schema, parity, and calculation suites
- Restored **Lakeflow Connect** as a first-class workload (catalog, form, calculator, sizing guide)
- Documented Databricks Support as commercial-only (not a workload form)
- Optional Unity Catalog pricing publication path (`pricing_source=unity_catalog`)
- Admin architecture note: when not to migrate the estimator to AppKit
- Lakebase cold-start: bounded jittered retries + atomic engine dispose before 503
- Persist Shutterstock / Lakebase PITR-snapshot / AI Parse UI fields correctly
- Installer job `notification_settings` + docs for optional failure email alerts
- Legacy `install_lakemeter.py` aligned to least-privilege grants helper
- Enable Postgres native login on Lakebase create **and** reuse (Issue #19)
- Root `ARCHITECTURE.md` / `CHANGELOG.md` reconciled with current DAB + SSO auth

---

## v0.1.1

*2026-08-01*

Patch release introducing safer upgrades and correcting AI Parse estimate persistence. No database schema or data migration is required.

### New capabilities

- Added a version-aware upgrade utility with `status`, `plan`, `doctor`, `apply`, and `rollback` commands
- Added immutable runtime staging, authenticated health checks, concurrency locks, resumable execution, and automatic recovery
- Added Lakebase backup branches for future minor data updates and major schema migrations; patch upgrades never modify Lakebase
- Updated new installations to provision Lakebase Autoscaling projects, branches, and endpoints directly

### Bug fixes

- Fixed AI Parse fields so calculation method, complexity, DBU quantity, page count, mode, and page volume persist and clone correctly

### Documentation updates

- Added the [Upgrade Guide](./admin-guide/upgrading.md) and updated installer and deployment documentation

---

## v0.1.0

*2026-07-24*

Initial public open-source release.

- Workload coverage for Jobs, All-Purpose, DBSQL, DLT/Lakeflow, Model Serving, FMAPI (Databricks + Proprietary), Vector Search, Lakebase, Databricks Apps, AI Parse, and Shutterstock ImageAI
- AI assistant with streaming chat, workload suggestions, and one-click accept
- Excel export with full cost breakdowns, SKU details, and discount calculations
- One-command installer (`scripts/install.sh`) using Databricks Asset Bundles
- Lakebase-backed estimate storage
- Multi-cloud support: AWS, Azure, GCP
- SSO authentication via Databricks Apps
- Interactive API docs at `/api/docs` and `/api/redoc`
