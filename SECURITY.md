# Security Policy

## Reporting a Vulnerability

Please **do not** open a public issue for security vulnerabilities.

Report vulnerabilities through [GitHub's private security advisories](https://github.com/alexxx-db/lakemeter-oss/security/advisories/new).
You can expect an acknowledgement within 3 business days. We will work
with you on a coordinated disclosure timeline.

## Supported Versions

Only the latest release receives security fixes. Fixes ship as patch
releases (see [RELEASING.md](RELEASING.md)); upgrade guidance is in
[the admin guide](docs-site/docs/admin-guide/upgrading.md).

## Dependency Scanning & SBOM

The `security.yml` CI workflow (run on every PR, push to `main`, and
weekly) provides two layers of supply-chain assurance:

- **Vulnerability scanning** — `pip-audit` against the installed Python
  environment (`backend/requirements.txt`) and `npm audit --omit=dev`
  for the frontend and docs site. Known-vulnerable dependency upgrades
  fail the build.
- **SBOM generation** — a CycloneDX SBOM is generated for both the
  Python and npm dependency trees on every run and uploaded as a build
  artifact, so each commit has an inspectable software bill of
  materials. Release-time SBOMs can be attached to GitHub Releases from
  the same workflow output.

## Secrets Handling

- All runtime secrets (database credentials) live in Databricks secret
  scopes and are injected as environment variables — never committed
  (see `scripts/notebooks/02_create_database.py`).
- Local development uses `.env` files, which are git-ignored.
- The diagnostics endpoint (`/api/v1/diagnostics`) masks every
  secret-bearing configuration value before returning its bundle.

## Authentication Notes

On Databricks Apps, the app's Service Principal authenticates to
Lakebase via OAuth (M2M) with automatic token refresh; a password-auth
role (`lakemeter_sync_role`) exists as a fallback for local development.
User-facing access is controlled by Databricks Apps workspace
authentication; see the admin guide for sharing and permissions.
