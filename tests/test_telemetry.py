"""Tests for opt-in telemetry.

Pins the privacy guarantees:
- disabled by default — no opt-in env vars means track_event is a no-op
- enabled requires BOTH TELEMETRY_ENABLED=true AND TELEMETRY_ENDPOINT
- the install id is a one-way hash (the raw host never appears)
- event properties are sanitized to scalars
- delivery failures are swallowed (telemetry must never break the app)
"""
import os
import sys

import pytest

BACKEND_DIR = os.path.join(os.path.dirname(__file__), '..', 'backend')
sys.path.insert(0, BACKEND_DIR)

from app import telemetry


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    for var in ("TELEMETRY_ENABLED", "TELEMETRY_ENDPOINT", "DATABRICKS_HOST"):
        monkeypatch.delenv(var, raising=False)
    yield


class TestOptInGate:
    def test_disabled_by_default(self):
        assert telemetry.telemetry_enabled() is False

    def test_enabled_flag_alone_is_not_enough(self, monkeypatch):
        monkeypatch.setenv("TELEMETRY_ENABLED", "true")
        assert telemetry.telemetry_enabled() is False

    def test_endpoint_alone_is_not_enough(self, monkeypatch):
        monkeypatch.setenv("TELEMETRY_ENDPOINT", "https://telemetry.example.com")
        assert telemetry.telemetry_enabled() is False

    def test_enabled_requires_both(self, monkeypatch):
        monkeypatch.setenv("TELEMETRY_ENABLED", "true")
        monkeypatch.setenv("TELEMETRY_ENDPOINT", "https://telemetry.example.com")
        assert telemetry.telemetry_enabled() is True

    @pytest.mark.parametrize("value", ["1", "true", "TRUE", "yes", "on"])
    def test_truthy_values(self, monkeypatch, value):
        monkeypatch.setenv("TELEMETRY_ENABLED", value)
        monkeypatch.setenv("TELEMETRY_ENDPOINT", "https://telemetry.example.com")
        assert telemetry.telemetry_enabled() is True


class TestTrackEvent:
    def test_noop_when_disabled(self, monkeypatch):
        import threading
        calls = []
        monkeypatch.setattr(threading, "Thread",
                            lambda *a, **k: calls.append((a, k)))
        telemetry.track_event("app_started")
        assert calls == []  # never even spawns a thread

    def test_posts_payload_when_enabled(self, monkeypatch):
        monkeypatch.setenv("TELEMETRY_ENABLED", "true")
        monkeypatch.setenv("TELEMETRY_ENDPOINT", "https://telemetry.example.com")
        monkeypatch.setenv("DATABRICKS_HOST", "https://adb-123.azuredatabricks.net")
        posted = []

        class _FakeThread:
            def __init__(self, target, args, daemon):
                self._target, self._args = target, args

            def start(self):
                self._target(*self._args)  # run synchronously for the test

        monkeypatch.setattr(telemetry.threading, "Thread", _FakeThread)
        import httpx
        monkeypatch.setattr(httpx, "post",
                            lambda url, json, timeout: posted.append((url, json)))

        telemetry.track_event("export_excel_generated",
                              {"line_item_count": 5, "cloud": "aws"})

        assert len(posted) == 1
        url, payload = posted[0]
        assert url == "https://telemetry.example.com"
        assert payload["event"] == "export_excel_generated"
        assert payload["properties"] == {"line_item_count": 5, "cloud": "aws"}
        assert payload["app_version"]
        assert isinstance(payload["timestamp"], int)
        # pseudonymous install id: present, but never the raw host
        assert payload["install_id"]
        assert "adb-123" not in str(payload)

    def test_properties_sanitized_to_scalars(self):
        clean = telemetry._sanitize_properties({
            "count": 3,
            "ok": True,
            "nested": {"drop": "me"},
            "a_list": [1, 2],
            "note": "kept",
        })
        assert clean == {"count": 3, "ok": True, "note": "kept"}

    def test_delivery_failure_is_swallowed(self, monkeypatch):
        monkeypatch.setenv("TELEMETRY_ENABLED", "true")
        monkeypatch.setenv("TELEMETRY_ENDPOINT", "https://telemetry.example.com")

        class _FakeThread:
            def __init__(self, target, args, daemon):
                self._target, self._args = target, args

            def start(self):
                self._target(*self._args)

        monkeypatch.setattr(telemetry.threading, "Thread", _FakeThread)
        import httpx

        def _boom(url, json, timeout):
            raise ConnectionError("unreachable")

        monkeypatch.setattr(httpx, "post", _boom)
        # must not raise
        telemetry.track_event("app_started")


class TestInstallId:
    def test_stable_and_hashed(self, monkeypatch):
        monkeypatch.setenv("DATABRICKS_HOST", "https://adb-123.azuredatabricks.net")
        first = telemetry.install_id()
        assert first == telemetry.install_id()
        assert len(first) == 16
        assert first != "https://adb-123.azuredatabricks.net"

    def test_differs_across_hosts(self, monkeypatch):
        monkeypatch.setenv("DATABRICKS_HOST", "https://host-a.com")
        a = telemetry.install_id()
        monkeypatch.setenv("DATABRICKS_HOST", "https://host-b.com")
        assert a != telemetry.install_id()
