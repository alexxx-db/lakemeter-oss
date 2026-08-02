"""Version-sync contract test for releases.

Pins every machine-readable version source to the repo-root VERSION file
and requires a matching dated changelog entry, so a release can never
ship with mismatched version metadata. Runs offline; no app imports.

Version sources (see RELEASING.md):
- VERSION
- frontend/package.json + package-lock.json
- docs-site/package.json + package-lock.json
- frontend/src/version.ts
- docs-site/docs/changelog.md (latest entry + date)
"""
import json
import os
import re

import pytest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

SEMVER_RE = re.compile(r'^\d+\.\d+\.\d+(?:[-.][0-9A-Za-z]+)?$')


def _read(path):
    with open(os.path.join(ROOT, path)) as f:
        return f.read()


def _version():
    return _read('VERSION').strip()


def _json_version(path):
    return json.loads(_read(path))['version']


def _lock_versions(path):
    data = json.loads(_read(path))
    versions = {data['version']}
    root_pkg = data.get('packages', {}).get('')
    if root_pkg is not None:
        versions.add(root_pkg['version'])
    return versions


def _version_ts():
    m = re.search(r"APP_VERSION = '([^']+)'", _read('frontend/src/version.ts'))
    assert m, "APP_VERSION not found in frontend/src/version.ts"
    return m.group(1)


CHANGELOG_HEADING_RE = re.compile(r'^## v(\d+\.\d+\.\d+(?:[-.][0-9A-Za-z]+)?)\s*$',
                                  re.M)
CHANGELOG_DATE_RE = re.compile(r'^\*\d{4}-\d{2}-\d{2}\*\s*$', re.M)


def _changelog_sections():
    """Yield (version, body) for each '## vX.Y.Z' section, newest first."""
    text = _read('docs-site/docs/changelog.md')
    matches = list(CHANGELOG_HEADING_RE.finditer(text))
    for i, m in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        yield m.group(1), text[m.end():end]


class TestVersionSync:
    def test_version_file_is_semver(self):
        assert SEMVER_RE.match(_version()), (
            f"VERSION '{_version()}' is not semver (X.Y.Z)")

    def test_all_machine_readable_sources_match(self):
        expected = _version()
        sources = {
            'frontend/package.json': {_json_version('frontend/package.json')},
            'frontend/package-lock.json': _lock_versions(
                'frontend/package-lock.json'),
            'docs-site/package.json': {_json_version('docs-site/package.json')},
            'docs-site/package-lock.json': _lock_versions(
                'docs-site/package-lock.json'),
            'frontend/src/version.ts': {_version_ts()},
        }
        mismatches = {
            name: sorted(vs) for name, vs in sources.items() if vs != {expected}
        }
        assert not mismatches, (
            f"Version sources out of sync with VERSION ({expected}): "
            f"{mismatches}. Run: python scripts/update_version.py {expected}")

    def test_changelog_latest_entry_matches_version(self):
        sections = list(_changelog_sections())
        assert sections, "no '## vX.Y.Z' entries in docs-site/docs/changelog.md"
        latest, _ = sections[0]
        assert latest == _version(), (
            f"changelog latest entry v{latest} != VERSION {_version()}. "
            f"Add a dated '## v{_version()}' section before releasing.")

    def test_changelog_latest_entry_is_dated(self):
        sections = list(_changelog_sections())
        assert sections
        latest, body = sections[0]
        assert CHANGELOG_DATE_RE.search(body), (
            f"changelog entry v{latest} has no '*YYYY-MM-DD*' date line")

    def test_changelog_versions_are_unique_and_semver(self):
        versions = [v for v, _ in _changelog_sections()]
        assert len(versions) == len(set(versions)), (
            f"duplicate changelog version entries: {versions}")
        for v in versions:
            assert SEMVER_RE.match(v), f"changelog version '{v}' is not semver"
