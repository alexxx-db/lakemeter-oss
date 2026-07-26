# Tasks & Roadmap

This file is the working plan for what happens next. It has three parts:

1. **Merge queue** — work already implemented, waiting to land.
2. **Operator checklist** — things only a repo admin / workspace admin can do.
3. **Roadmap** — planned work, in priority order, with enough context to pick any item up cold.

When you complete an item, delete it here (and mention it in the changelog). Keep this file short enough to read in one sitting — prune aggressively.

---

## 1. Merge queue

All branches are verified: full test suite run against pristine `main`, byte-identical
push verification. Merge in this order to minimize conflicts.

**Chain (order matters):**
`#2 → #1 → #3 → #4 → #5 → #8 → #12 → #6 → #15 → #16 → #7`

- After #4 and #7 both land, resolve the known overlap in
  `backend/app/database.py` by taking PR #7's version (its OAuth/creator model is
  the one the readiness endpoint and token refresh were built against).

**Independent PRs (merge any time, off `main`):**
`#9, #10, #11 → #13, #14, #17, #18, #21, #22, #23`

- #13 must come after #11 (golden pack builds on the export VM pricing branch).
- #14, #17, #18, #21, #22, #23 touch disjoint files and can land in any order.
- #16 is chained on #15.

After each merge, re-run the full test suite on the merge result before merging the
next chained PR.

---

## 2. Operator checklist (requires repo / workspace admin)

These cannot be done from a pull request; they need repository settings or the
Databricks workspace.

- [ ] **Apply the four workflow files.** The token used for automation lacks the
  `workflow` OAuth scope, so the revised YAMLs are posted as comments:
  - `ci.yml` — comment on PR #4 (includes the pricing-coverage matrix job in a follow-up comment)
  - `bundle.yml` — comment on PR #6
  - `release.yml` — comment on PR #14
  - `security.yml` — comment on PR #17

  Either copy each file from its comment into `.github/workflows/`, or re-authorize
  the automation token with the `workflow` scope and ask for them to be pushed.
- [ ] **Add CI secrets** (repo Settings → Secrets and variables → Actions):
  `DATABRICKS_HOST`, `DATABRICKS_CLIENT_ID`, `DATABRICKS_CLIENT_SECRET`,
  `LAKEBASE_INSTANCE_NAME`. Needed by the integration and bundle-validation jobs.
- [ ] **Enable branch protection on `main`** with required checks:
  `python-checks`, `integration-postgres`, `frontend-build`, `docs-build`,
  `validate` (bundle), `pricing-coverage`. Require two-person review.
- [ ] **Create the GitHub environments** referenced by `bundle.yml`
  (deployment approval gates).
- [ ] **First manual release dry-run**: tag `v0.2.0` on a throwaway clone and walk
  `RELEASING.md` end to end before the real release.

---

## 3. Roadmap

### 3.1 In-flight tracking items (time-sensitive)

- **Issue #19 — Lakebase password-auth default change.**
  New Lakebase Autoscaling projects created after 2026-05-21 have PostgreSQL
  password authentication *disabled by default*. The installer falls back to a
  password-auth role (`lakemeter_sync_role`) when service-principal OAuth isn't
  configured; on new projects that fallback will fail unless password auth is
  explicitly enabled on the project.
  *Action:* verify the fallback path on a freshly created project; either enable
  password auth during provisioning (`01_provision_lakebase.py`) or make the SP
  OAuth path mandatory. Update `docs-site/docs/admin-guide/installer.md` accordingly.
- **Issue #20 — Gemini 2.5 pricing data retirement (deadline 2026-10-16).**
  The Gemini 2.5 model family retires 2026-10-16. The bundled
  `fmapi-proprietary-rates` data contains these models.
  *Action:* refresh FMAPI proprietary rates after the retirement (re-run
  `etl/pricing_sync/12_Load_FMAPI_Proprietary_Rates` or the bundled CSV update),
  ship in the next release, and confirm the UI's model dropdown reflects the change.

### 3.2 Next releases

**v0.2.0 — Productionalization release (target: after merge queue clears)**
Contents: everything in the changelog's Unreleased section. Exit criteria:
all PRs merged, workflows applied, CI green on `main`, version bumped via
`scripts/update_version.py`, tag-driven release executed.

**v0.3.0 — Marketplace submission (Public Preview)**
Prereq: v0.2.0 shipped. Work items:
- [ ] Complete the partner readiness checklist in `marketplace/README.md`
  (dependency pinning is the main ⚠️ — move `requirements.txt` from `>=` ranges to
  pinned versions with hashes for the release build).
- [ ] SEG-restricted workspace install test (marketplace requirement).
- [ ] Two-person review / branch protection evidence (operator checklist above).
- [ ] Submit listing per the steps in `marketplace/README.md`.

### 3.3 Engineering improvements (no release dependency)

Ordered by value-per-effort:

1. **Pin runtime dependencies.** Replace `>=` ranges in `requirements.txt` with
   exact pins (or a lock file) so releases are bit-reproducible. Keep ranges in a
   `requirements-dev.txt` if desired.
2. **Reduce test-suite environment coupling.** ~1,065 of the failures in a sandbox
   run are credential-gated suites failing for lack of a workspace. Split
   `pyproject.toml` markers so `pytest -m "not databricks and not e2e"` is a clean
   signal locally and in CI.
3. **SQL calculator coverage for remaining workload types.** Lakebase CU pricing,
   AI Parse, Shutterstock, Databricks Apps, and Lakeflow Connect are computed in
   Python only (ADR-004). Port them to SQL functions so the notebook/SQL audience
   gets them too, and add matching `etl/lakebase_setup/tests/Test_*.py` notebooks.
4. **Pricing data diff report.** A small script that diffs two bundled snapshots
   and emits a human-readable "what changed in the price list" section for release
   notes. Natural input to the release workflow.
5. **Migration ledger.** ADR-005's idempotent notebooks work, but there's no record
   of *which* migrations a given installation has applied. Add a
   `lakemeter.schema_migrations` table written by each installer notebook.
6. **Decision-record surfacing.** `decision_records` rows written by the AI
   assistant are stored but not yet exposed in the UI. A read-only "why did the
   assistant suggest this" panel would close the loop.

### 3.4 Known limitations (documented, not scheduled)

- Rollback of database changes is restore-from-backup, not down-migrations
  (see ADR-005). Plan upgrades accordingly; the upgrade guide says to snapshot
  first.
- Telemetry is intentionally minimal (two events: app start, Excel export). If more
  events are added, update the privacy note in `backend/app/telemetry.py` and
  `marketplace/README.md`'s egress declaration.
- The `line_items` table is wide (~80 columns) by design: every workload type's
  parameters share one table. If it grows much further, consider splitting
  rarely-used workload-specific columns into JSONB `workload_config` (which already
  exists as a fallback).
