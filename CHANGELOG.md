# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project adheres to
[Semantic Versioning](https://semver.org/):

- **Major** (X.0.0) — breaking changes, mandatory database migrations
- **Minor** (0.X.0) — new features, new workload types
- **Patch** (0.0.X) — bug fixes, pricing data updates

This root changelog is the canonical engineering source. The published docs site
mirrors release notes in `docs-site/docs/changelog.md` (version-sync tests pin
dated `## vX.Y.Z` entries there to `VERSION`).

---

## [Unreleased]

Security, trust, and platform hardening on top of v0.1.1 (also summarized in
`docs-site/docs/changelog.md`).

### Security / AuthZ
- Locked down user APIs (no open list/create); self-or-admin updates only
- Bound AI chat conversations to SSO ownership
- Removed unused production JWT gate (Apps SSO identity headers only)

### Trust / Lakebase
- Least-privilege Lakebase grants via `scripts/lakebase_grants.py` (DAB notebooks
  and legacy `install_lakemeter.py`)
- Pricing freshness metadata + paused weekly job `lakemeter_pricing_refresh`
  + UI “prices as of”; optional `pricing_source=unity_catalog`
- Durable AI conversation persistence (`ai_conversations`)
- Lakebase cold-start: bounded jittered retries + atomic engine dispose
- Enable Postgres native login on create **and** reuse (`enable_pg_native_login`)
  so password-auth fallback works on post–2026-05-21 projects (Issue #19)

### Product / docs
- Restored Lakeflow Connect as a first-class workload
- Documented Databricks Support as commercial-only
- Admin guides: pricing data path, AppKit evaluation note
- Persist Shutterstock / Lakebase PITR-snapshot / AI Parse UI fields correctly

### Ops / CI
- Installer DAB targets (`dev`/`staging`/`prod`), timeouts, notification_settings
- Expanded offline CI (schema, parity, calculation, grants, version sync, cloud pricing)

### Previously queued (earlier Unreleased PRs)
- Golden-estimate test pack, version-sync guard, tag-driven release docs
- Upgrade guide, SECURITY.md, readiness/diagnostics endpoints, optional telemetry
- Marketplace readiness pack, multi-cloud pricing coverage tests

---

## [0.1.1] — 2026-08-01

Patch release introducing safer upgrades and correcting AI Parse estimate persistence.
See `docs-site/docs/changelog.md` for the full notes.

---

## [0.1.0] — 2026-07-24

Initial public open-source release.

### Added
- Workload coverage for Jobs, All-Purpose, DBSQL, DLT/Lakeflow, Model Serving,
  FMAPI (Databricks + Proprietary), Vector Search, Lakebase, Databricks Apps,
  AI Parse, and Shutterstock ImageAI.
- AI assistant with streaming chat, workload suggestions, and one-click accept.
- Excel export with full cost breakdowns, SKU details, and discount calculations.
- One-command installer (`scripts/install.sh`) using Databricks Asset Bundles.
- Lakebase-backed estimate storage (schema `lakemeter`, database `lakemeter_pricing`).
- SQL cost-calculation functions deployed into Lakebase
  (`scripts/functions/01–09`, orchestrated by `calculate_line_item_costs`).
- Bundled pricing snapshot covering AWS, Azure, and GCP.
- Unity Catalog pricing-fetch notebooks (`etl/pricing_sync/`).
- Multi-cloud support: AWS, Azure, GCP.
- SSO authentication via Databricks Apps.
- Interactive API docs at `/api/docs` and `/api/redoc`.

[Unreleased]: https://github.com/databrickslabs/lakemeter-oss/compare/v0.1.1...HEAD
[0.1.1]: https://github.com/databrickslabs/lakemeter-oss/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/databrickslabs/lakemeter-oss/releases/tag/v0.1.0
