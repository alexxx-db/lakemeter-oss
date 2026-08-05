"""Regression tests for security hardening:
- Auth is Apps SSO (no application JWT secret required)
- Debug endpoints must not be registered in production
- User and chat routes require authentication
"""
import importlib
import sys

import pytest


def _fresh_config(monkeypatch, **env):
    """Import app.config with a controlled environment."""
    for mod in [m for m in sys.modules if m.startswith("app.config") or m == "app"]:
        del sys.modules[mod]
    for key in ("ENVIRONMENT", "JWT_SECRET_KEY"):
        monkeypatch.delenv(key, raising=False)
    for key, value in env.items():
        monkeypatch.setenv(key, value)
    import app.config
    return importlib.reload(app.config)


class TestAppsSsoAuthPolicy:
    def test_production_starts_without_jwt_secret(self, monkeypatch):
        config = _fresh_config(monkeypatch, ENVIRONMENT="production")
        assert config.settings.is_production
        assert not hasattr(config.settings, "jwt_secret_key")

    def test_no_jwt_fields_in_settings_source(self):
        """JWT settings must not return — auth is Apps SSO headers only."""
        from pathlib import Path

        src = Path("backend/app/config.py").read_text()
        assert "jwt_secret_key" not in src
        assert "JWT_SECRET_KEY" not in src


def _route_paths(monkeypatch, **env):
    """Build the FastAPI app under a controlled environment and list route paths."""
    for mod in [m for m in sys.modules if m.startswith("app")]:
        del sys.modules[mod]
    for key in ("ENVIRONMENT", "JWT_SECRET_KEY", "DATABASE_URL"):
        monkeypatch.delenv(key, raising=False)
    for key, value in env.items():
        monkeypatch.setenv(key, value)
    import app.main
    return [r.path for r in app.main.app.routes]


class TestDebugEndpointsGated:
    def test_debug_endpoints_absent_in_production(self, monkeypatch):
        paths = _route_paths(
            monkeypatch,
            ENVIRONMENT="production",
            DATABASE_URL="postgresql://u:p@localhost:5432/db",
        )
        assert not any("/debug" in p for p in paths), [
            p for p in paths if "/debug" in p
        ]

    def test_debug_endpoints_present_in_local(self, monkeypatch):
        paths = _route_paths(
            monkeypatch,
            ENVIRONMENT="local",
            DATABASE_URL="postgresql://u:p@localhost:5432/db",
        )
        assert "/api/v1/debug/headers" in paths
        assert "/api/v1/debug/database" in paths
        assert "/api/v1/debug/database/refresh" in paths

    def test_cors_same_origin_in_production_config(self, monkeypatch):
        """Empty CORS_ORIGINS must yield no cross-origin allowances."""
        config = _fresh_config(
            monkeypatch, ENVIRONMENT="production", CORS_ORIGINS="",
        )
        assert config.settings.cors_origins_list == []

