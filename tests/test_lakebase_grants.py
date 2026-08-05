"""Static checks for least-privilege Lakebase grant helpers."""
import ast
import os
import sys

SCRIPTS_DIR = os.path.join(os.path.dirname(__file__), "..", "scripts")
sys.path.insert(0, SCRIPTS_DIR)

from lakebase_grants import APP_WRITE_TABLES, grant_app_role_sql


def test_app_write_tables_cover_core_entities():
    required = {
        "users",
        "estimates",
        "line_items",
        "sharing",
        "templates",
        "conversation_messages",
        "decision_records",
        "ai_conversations",
    }
    assert required.issubset(set(APP_WRITE_TABLES))


def test_grants_are_least_privilege():
    stmts = grant_app_role_sql("app-sp-id", "lakemeter_pricing")
    joined = "\n".join(stmts)
    assert "ALL PRIVILEGES" not in joined
    assert "GRANT SELECT ON ALL TABLES" in joined
    assert "GRANT EXECUTE ON ALL FUNCTIONS" in joined
    for table in APP_WRITE_TABLES:
        assert f'GRANT INSERT, UPDATE, DELETE ON TABLE "lakemeter"."{table}"' in joined or \
               f"GRANT INSERT, UPDATE, DELETE ON TABLE \"lakemeter\".\"{table}\"" in joined


def test_installer_notebooks_use_shared_grants_helper():
    for relative in (
        "notebooks/05b_grant_app_access.py",
        "notebooks/02_create_database.py",
        "notebooks/05_configure_app.py",
    ):
        path = os.path.join(SCRIPTS_DIR, relative)
        text = open(path).read()
        assert "apply_app_role_grants" in text, f"{relative} should use apply_app_role_grants"
        assert "GRANT ALL PRIVILEGES ON ALL TABLES" not in text, (
            f"{relative} still grants ALL PRIVILEGES on tables"
        )


def test_grant_sql_is_valid_python_module():
    path = os.path.join(SCRIPTS_DIR, "lakebase_grants.py")
    ast.parse(open(path).read())
