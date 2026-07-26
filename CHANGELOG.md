# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project adheres to
[Semantic Versioning](https://semver.org/):

- **Major** (X.0.0) — breaking changes, mandatory database migrations
- **Minor** (0.X.0) — new features, new workload types
- **Patch** (0.0.X) — bug fixes, pricing data updates

This root changelog is the canonical source; `docs-site/docs/changelog.md` mirrors it
for the published documentation site. The version-sync test suite enforces that the
latest entry here matches `VERSION` and carries a date.

---

## [Unreleased]

The following changes are implemented on pull-request branches and queued for merge
(see TASKS.md for the merge order). They will be folded into the next tagged release.

### Added
- Golden-estimate test pack (`tests/export/golden/`): a canonical 9-workload estimate
  with independently derived expected values, pinning the cost model against
  accidental change (PR #13).
- Version-sync guard (`tests/test_version_sync.py`): CI fails if `VERSION`,
  frontend/docs package files, lockfiles, `frontend/src/version.ts`, or the latest
  dated changelog entry disagree (PR #14).
- Tag-driven release flow documented in `RELEASING.md` (PR #14).
- Scheduled pricing-sync job `lakemeter_pricing_sync` in `scripts/databricks.yml`
  (monthly, 06:00 UTC on the 1st; paused by default; enable with
  `--var="pricing_sync_pause_status=UNPAUSED"`) (PR #15).
- Upgrade guide (`docs-site/docs/admin-guide/upgrading.md`): version check,
  data-preservation matrix, standard upgrade, rollback (PR #16).
- `SECURITY.md`: private vulnerability reporting, supported versions, dependency
  scanning and SBOM notes (PR #17).
- Readiness endpoint `GET /health/ready` (200 only when the database is reachable
  *and* core pricing tables are populated) and diagnostics endpoint
  `GET /api/v1/diagnostics` (version, system info, redacted config, DB status, table
  row counts, pool status) (PR #18).
- Optional structured JSON logging via `LOG_FORMAT=json` (PR #18).
- Opt-in telemetry module (`backend/app/telemetry.py`): disabled unless both
  `TELEMETRY_ENABLED` and `TELEMETRY_ENDPOINT` are set; salted-hashed install ID;
  fire-and-forget delivery that can never break a request (PR #21).
- Multi-cloud pricing coverage tests (`tests/test_pricing_data_clouds.py`): 36 checks
  that the bundled pricing snapshot covers AWS, Azure, and GCP across every rate file
  (PR #22).
- Marketplace readiness pack (`marketplace/README.md`): listing draft, resource and
  egress declarations, 23-item readiness checklist (PR #23).

### Fixed / Hardened (from earlier queued PRs)
- Backend lint cleanup and CI workflow (PR #4; revised workflow YAML posted as PR comment).
- Databricks Asset Bundle packaging and bundle validation workflow (PR #6; revised YAML in comment).
- Lakebase connectivity improvements, including OAuth token refresh (PR #7).
- Export VM pricing corrections (PR #12).

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
- Bundled pricing snapshot (`backend/static/pricing/`) covering AWS, Azure, and GCP.
- Unity Catalog pricing-fetch notebooks (`etl/pricing_sync/`) targeting
  `lakemeter_catalog.lakemeter.*`.
- Multi-cloud support: AWS, Azure, GCP.
- SSO authentication via Databricks Apps.
- Interactive API docs at `/api/docs` and `/api/redoc`.

[Unreleased]: https://github.com/alexxx-db/lakemeter-oss/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/alexxx-db/lakemeter-oss/releases/tag/v0.1.0
