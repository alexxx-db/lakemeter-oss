"""Least-privilege Lakebase grants for Lakemeter application roles.

App roles may:
- SELECT any table in schema lakemeter (pricing + app data)
- INSERT/UPDATE/DELETE only on application tables
- USAGE/SELECT on sequences
- EXECUTE on functions (cost calculators)

They must not receive ALL PRIVILEGES or CREATE on the schema.
"""
from __future__ import annotations

from typing import Iterable

# Tables the app mutates at runtime (SSO users, estimates, sharing, AI audit).
APP_WRITE_TABLES = (
    "users",
    "templates",
    "estimates",
    "line_items",
    "conversation_messages",
    "decision_records",
    "sharing",
    "ai_conversations",
)

SCHEMA = "lakemeter"


def quote_ident(ident: str) -> str:
    """Quote a Postgres identifier (role names may contain hyphens/UUIDs)."""
    return '"' + ident.replace('"', '""') + '"'


def grant_app_role_sql(
    role_name: str,
    database_name: str,
    schema: str = SCHEMA,
    write_tables: Iterable[str] = APP_WRITE_TABLES,
) -> list[str]:
    """Return SQL statements that apply least-privilege grants to role_name."""
    role = quote_ident(role_name)
    schema_q = quote_ident(schema)
    stmts = [
        f"GRANT CONNECT ON DATABASE {quote_ident(database_name)} TO {role}",
        f"GRANT USAGE ON SCHEMA {schema_q} TO {role}",
        # Start clean on re-runs / upgrades
        f"REVOKE ALL ON ALL TABLES IN SCHEMA {schema_q} FROM {role}",
        f"REVOKE ALL ON ALL SEQUENCES IN SCHEMA {schema_q} FROM {role}",
        f"REVOKE ALL ON ALL FUNCTIONS IN SCHEMA {schema_q} FROM {role}",
        # Read pricing + app data
        f"GRANT SELECT ON ALL TABLES IN SCHEMA {schema_q} TO {role}",
        f"GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA {schema_q} TO {role}",
        f"GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA {schema_q} TO {role}",
    ]
    for table in write_tables:
        stmts.append(
            f"GRANT INSERT, UPDATE, DELETE ON TABLE {schema_q}.{quote_ident(table)} TO {role}"
        )
    # Future objects created by the current (owner) role
    stmts.extend(
        [
            f"ALTER DEFAULT PRIVILEGES IN SCHEMA {schema_q} "
            f"REVOKE ALL ON TABLES FROM {role}",
            f"ALTER DEFAULT PRIVILEGES IN SCHEMA {schema_q} "
            f"GRANT SELECT ON TABLES TO {role}",
            f"ALTER DEFAULT PRIVILEGES IN SCHEMA {schema_q} "
            f"GRANT USAGE, SELECT ON SEQUENCES TO {role}",
            f"ALTER DEFAULT PRIVILEGES IN SCHEMA {schema_q} "
            f"GRANT EXECUTE ON FUNCTIONS TO {role}",
        ]
    )
    return stmts


def apply_app_role_grants(cursor, role_name: str, database_name: str) -> int:
    """Execute least-privilege grants. Returns number of statements run."""
    stmts = grant_app_role_sql(role_name, database_name)
    for sql in stmts:
        cursor.execute(sql)
    return len(stmts)
