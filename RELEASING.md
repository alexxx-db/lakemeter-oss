# Releasing Lakemeter OSS

Lakemeter uses Semantic Versioning (`vMAJOR.MINOR.PATCH`) for public releases.

## Version Sources

The release version is recorded in:

- `VERSION`
- `frontend/package.json`
- `frontend/package-lock.json`
- `docs-site/package.json`
- `docs-site/package-lock.json`
- `frontend/src/version.ts`
- `docs-site/docs/changelog.md`

Use the version sync helper to keep the machine-readable files aligned:

```bash
python scripts/update_version.py 0.1.0
```

The changelog should still be reviewed and edited by hand for human-readable release notes.

## Version Sync Guard

`tests/test_version_sync.py` pins every source above to `VERSION` and
requires a dated `## vX.Y.Z` changelog entry matching it. It runs in CI
and again in the release workflow, so mismatched metadata can never
reach a release. Between releases, `VERSION` on `main` stays at the last
released version; bump it only as part of release prep.

```bash
python -m pytest tests/test_version_sync.py -q
```

## Automated Release Flow (tag-driven)

Pushing a `vX.Y.Z` tag runs `.github/workflows/release.yml`, which:

1. Runs the version-sync guard.
2. Verifies the tag matches `VERSION`.
3. Extracts the tag's section from `docs-site/docs/changelog.md` and
   publishes a GitHub Release with those notes.

Release prep therefore reduces to:

```bash
python scripts/update_version.py <version>
# edit docs-site/docs/changelog.md — add the dated <version> section
python -m pytest tests/test_version_sync.py -q
git add VERSION frontend docs-site && git commit -m "Release v<version>"
git tag -a v<version> -m "Lakemeter OSS v<version>"
git push origin main v<version>
```

## Manual Release Flow (fallback)

1. Update version metadata:

   ```bash
   python scripts/update_version.py <version>
   ```

2. Update `docs-site/docs/changelog.md`.

3. Run checks:

   ```bash
   python -m pytest tests/schema/test_line_item_schema_alignment.py -q
   (cd frontend && npm run build)
   (cd docs-site && npm run build)
   ```

4. Commit the release metadata:

   ```bash
   git add VERSION frontend/package.json frontend/package-lock.json docs-site/package.json docs-site/package-lock.json frontend/src/version.ts docs-site/docs/changelog.md backend/static
   git commit -m "Release v<version>"
   git push databrickslabs main
   ```

5. Create an annotated tag:

   ```bash
   git tag -a v<version> -m "Lakemeter OSS v<version>"
   git push databrickslabs v<version>
   ```

6. Create a GitHub Release:

   ```bash
   gh release create v<version> \
     --repo databrickslabs/lakemeter-oss \
     --title "Lakemeter OSS v<version>" \
     --notes-file <release-notes-file>
   ```

## Version Bump Guidelines

- Patch (`v0.1.1`): bug fixes, pricing data updates, documentation fixes.
- Minor (`v0.2.0`): new workload support, new user-facing features, installer improvements.
- Major (`v1.0.0`): stable API/installer contract or breaking changes.
