"""Regression tests for security hardening:
- JWT secret must be explicit in production (no shipped/predictable default)
- Debug endpoints must not be registered in production
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


class TestJwtSecretPolicy:
    def test_production_requires_jwt_secret(self, monkeypatch):
        with pytest.raises(Exception, match="JWT_SECRET_KEY"):
            _fresh_config(monkeypatch, ENVIRONMENT="production")

    def test_production_rejects_placeholder_secret(self, monkeypatch):
        with pytest.raises(Exception, match="placeholder"):
            _fresh_config(
                monkeypatch,
                ENVIRONMENT="production",
                JWT_SECRET_KEY="your-secret-key-change-in-production",
            )

    def test_production_accepts_explicit_secret(self, monkeypatch):
        config = _fresh_config(
            monkeypatch, ENVIRONMENT="production", JWT_SECRET_KEY="real-secret-value"
        )
        assert config.settings.jwt_secret_key == "real-secret-value"

    def test_local_generates_ephemeral_secret(self, monkeypatch):
        config = _fresh_config(monkeypatch, ENVIRONMENT="local")
        assert config.settings.jwt_secret_key  # non-empty
        assert config.settings.jwt_secret_key != "your-secret-key-change-in-production"

    def test_no_insecure_default_in_source(self):
        """The old hardcoded default must never come back."""
        from pathlib import Path

        src = Path("backend/app/config.py").read_text()
        assert 'jwt_secret_key: str = "your-secret-key-change-in-production"' not in src


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
            JWT_SECRET_KEY="real-secret-value",
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
            monkeypatch, ENVIRONMENT="production",
            JWT_SECRET_KEY="real-secret-value", CORS_ORIGINS="",
        )
        assert config.settings.cors_origins_list == []
