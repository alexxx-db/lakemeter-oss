"""Regression tests: calculate / reference / vm-pricing / workload-types
routers must require an authenticated user (Databricks Apps forwarded identity).

These endpoints previously had no auth dependency at all — reachable by anyone
who could reach the app process (direct-origin access bypassing the Apps SSO
proxy, or a non-Apps deployment). They now 401 without a user identity header.
"""
import sys

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="module")
def client(monkeypatch_module):
    """TestClient for the app with a dummy (unreachable) database URL.

    Endpoints may fail downstream with 400/422/500 due to the missing DB —
    that's fine; these tests only assert on the 401 boundary.
    """
    for mod in [m for m in sys.modules if m.startswith("app")]:
        del sys.modules[mod]
    monkeypatch_module.setenv("DATABASE_URL", "postgresql://u:p@localhost:5432/db")
    monkeypatch_module.delenv("LOCAL_DEV_EMAIL", raising=False)
    import app.main
    return TestClient(app.main.app)


@pytest.fixture(scope="module")
def monkeypatch_module():
    from _pytest.monkeypatch import MonkeyPatch
    mp = MonkeyPatch()
    yield mp
    mp.undo()


AUTH_HEADER = {"X-Forwarded-Email": "tester@example.com"}

PROTECTED_GET_ROUTES = [
    # Reference data routes mount directly under /api/v1 (no /reference prefix)
    "/api/v1/regions?cloud=aws",
    "/api/v1/tiers?cloud=aws",
    "/api/v1/vm-pricing/regions",
    "/api/v1/vm-pricing/instance-types",
    "/api/v1/workload-types/",
]

PROTECTED_POST_ROUTES = [
    "/api/v1/calculate/jobs-classic",
    "/api/v1/calculate/all-purpose-classic",
    "/api/v1/calculate/model-serving",
]


class TestUnauthenticatedRequestsRejected:
    @pytest.mark.parametrize("path", PROTECTED_GET_ROUTES)
    def test_get_routes_401_without_identity_header(self, client, path):
        resp = client.get(path)
        assert resp.status_code == 401, f"GET {path} returned {resp.status_code}"

    @pytest.mark.parametrize("path", PROTECTED_POST_ROUTES)
    def test_post_routes_401_without_identity_header(self, client, path):
        resp = client.post(path, json={})
        assert resp.status_code == 401, f"POST {path} returned {resp.status_code}"


class TestAuthenticatedRequestsPassAuthGate:
    """With the Databricks Apps identity header the request must get past auth.

    Downstream failures (400 validation / 422 missing body / 500 no DB) are
    acceptable — only 401/403 would indicate an auth regression.
    """

    @pytest.mark.parametrize("path", PROTECTED_GET_ROUTES)
    def test_get_routes_pass_auth_with_identity_header(self, client, path):
        resp = client.get(path, headers=AUTH_HEADER)
        assert resp.status_code not in (401, 403), \
            f"GET {path} returned {resp.status_code} despite identity header"

    @pytest.mark.parametrize("path", PROTECTED_POST_ROUTES)
    def test_post_routes_pass_auth_with_identity_header(self, client, path):
        resp = client.post(path, json={}, headers=AUTH_HEADER)
        assert resp.status_code not in (401, 403), \
            f"POST {path} returned {resp.status_code} despite identity header"


class TestUnprotectedRoutesStayOpen:
    """Health and API root must remain reachable for platform health checks."""

    def test_health_endpoint_open(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200

    def test_api_root_open(self, client):
        resp = client.get("/api")
        assert resp.status_code == 200


class TestLocalDevBypass:
    """LOCAL_DEV_EMAIL simulates a user for local development."""

    def test_local_dev_email_grants_access(self, monkeypatch):
        for mod in [m for m in sys.modules if m.startswith("app")]:
            del sys.modules[mod]
        monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@localhost:5432/db")
        monkeypatch.setenv("LOCAL_DEV_EMAIL", "dev@example.com")
        import importlib
        import app.main
        importlib.reload(app.main)
        local_client = TestClient(app.main.app)
        resp = local_client.get("/api/v1/regions?cloud=aws")
        assert resp.status_code != 401
