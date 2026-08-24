"""SQLite must be rejected with a clear error (Lakemeter requires
Lakebase/PostgreSQL — the cost-calculation SQL functions run in the database,
and the engine is configured with PostgreSQL-specific pooling args)."""
import sys

import pytest


def _get_database_url(monkeypatch, url):
    for mod in [m for m in sys.modules if m.startswith("app.database")]:
        del sys.modules[mod]
    monkeypatch.setenv("DATABASE_URL", url)
    import app.database
    return app.database._get_database_url()


class TestSqliteRejected:
    @pytest.mark.parametrize("url", [
        "sqlite:///:memory:",
        "sqlite:///./test.db",
        "SQLite:///:memory:",
    ])
    def test_sqlite_urls_fail_fast(self, monkeypatch, url):
        with pytest.raises(Exception, match="SQLite is not supported"):
            _get_database_url(monkeypatch, url)

    def test_postgres_url_accepted(self, monkeypatch):
        assert _get_database_url(
            monkeypatch, "postgresql://u:p@localhost:5432/db"
        ) == "postgresql://u:p@localhost:5432/db"
