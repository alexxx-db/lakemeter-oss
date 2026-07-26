---
sidebar_position: 7
---

# Upgrading Lakemeter

How to move an existing Lakemeter installation to a newer release — what
is preserved, what is refreshed, and how to roll back.

## Check your version

- **Installed version:** shown in the app footer
  (`Lakemeter OSS vX.Y.Z`).
- **Latest release:** see the
  [GitHub Releases](https://github.com/alexxx-db/lakemeter-oss/releases)
  page and the [changelog](https://github.com/alexxx-db/lakemeter-oss/blob/main/docs-site/docs/changelog.md)
  for what changed in each version.

## What is preserved

Your data lives in the Lakebase database and is **never dropped** by an
upgrade:

| Data | Tables | Upgrade behavior |
|------|--------|------------------|
| Estimates, line items, templates | `estimates`, `line_items`, `templates`, `sharing` | Preserved |
| Users, conversations, decisions | `users`, `conversation_messages`, `decision_records` | Preserved |
| Pricing reference data | `sync_*`, `ref_*` tables | **Refreshed** to the new release's snapshot (`TRUNCATE + INSERT`) |
| Secrets & app config | `lakemeter-secrets`, app resources | Reused (no re-entry needed) |

The installer creates tables with `IF NOT EXISTS` and only the pricing
sync tables are reloaded — user data is never truncated.

## Standard upgrade

```bash
# 1. Fetch the new release
cd lakemeter-oss
git fetch --tags
git checkout v<new-version>

# 2. Rebuild the frontend and deploy (day-2 bundle)
./deploy.sh
databricks bundle deploy --target prod
databricks bundle run lakemeter --target prod
```

Or re-run the installer instead — it is idempotent and additionally
picks up new stored functions and pricing data in one pass:

```bash
./scripts/install.sh --profile <cli-profile> --non-interactive
```

There is **no downtime window to manage**: the app redeploys in place,
and Lakebase keeps serving the existing tables throughout.

## Refresh pricing after an upgrade

New releases ship refreshed pricing data. After deploying, reconcile the
Lakebase `sync_*` tables with the new snapshot using any of:

- **Scheduled sync job** — if you enabled the *Lakemeter Pricing Sync*
  schedule (see [Scheduled Pricing Sync](./installer#scheduled-pricing-sync)),
  it refreshes automatically on the 1st of the month; trigger
  **Run now** in the Workflows UI for an immediate refresh
- **Installer re-run** — reloads pricing data as part of the pass

## Rollback

Each release is a tagged, self-contained snapshot:

```bash
git checkout v<previous-version>
./deploy.sh
databricks bundle deploy --target prod
databricks bundle run lakemeter --target prod
```

If the newer release also refreshed pricing data and you need the prior
snapshot, re-run the installer from the previous tag (or trigger the
sync job from a checkout of that tag) to reload its CSVs.

## Version-specific notes

Breaking changes and required manual steps (if any) are called out in
the changelog entry for each release — review the entries between your
installed version and the target version before upgrading. Lakemeter
follows SemVer: patch releases are always safe to apply, minor releases
add features without breaking changes, and anything requiring action is
a major release with explicit migration notes.
