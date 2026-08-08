# Databricks notebook source
# MAGIC %md
# MAGIC # 11: Apply Schema Migrations
# MAGIC
# MAGIC Canonical schema manager for the Lakemeter pipeline tables. Migration
# MAGIC files live in `./migrations/` next to this notebook (they deploy with
# MAGIC the bundle because they sit under `notebooks/`) and are applied in
# MAGIC filename order. Each migration is recorded in
# MAGIC `lakemeter.schema_migrations` with a SHA-256 checksum:
# MAGIC
# MAGIC - Pending migrations are applied inside a transaction and recorded.
# MAGIC - Already-applied migrations are skipped.
# MAGIC - A checksum mismatch on an applied migration means someone edited a
# MAGIC   file after it shipped: the run fails loudly instead of silently
# MAGIC   diverging schema. Fix by writing a new migration, never by editing
# MAGIC   an applied one.
# MAGIC
# MAGIC This task runs first in the daily pipeline so every downstream task
# MAGIC can assume the schema exists.

# COMMAND ----------

dbutils.widgets.text("instance_name", "lakemeter-customer")
dbutils.widgets.text("db_name", "lakemeter_pricing")
dbutils.widgets.text("secrets_scope", "lakemeter-secrets")

instance_name = dbutils.widgets.get("instance_name")
db_name = dbutils.widgets.get("db_name")
secrets_scope = dbutils.widgets.get("secrets_scope")

# COMMAND ----------

import hashlib
import os
from datetime import date
from pathlib import Path

import psycopg2
from databricks.sdk import WorkspaceClient

w = WorkspaceClient()
instance = w.database.get_database_instance(instance_name)
cred = w.database.generate_database_credential(
    request_id=str(date.today()), instance_names=[instance_name]
)
conn = psycopg2.connect(
    host=instance.read_write_dns,
    port=5432,
    dbname=db_name,
    user=w.current_user.me().user_name,
    password=cred.token,
    sslmode="require",
)
conn.autocommit = False
cur = conn.cursor()

# COMMAND ----------

cur.execute("""
CREATE TABLE IF NOT EXISTS lakemeter.schema_migrations (
    migration_id TEXT PRIMARY KEY,
    checksum TEXT NOT NULL,
    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")
conn.commit()

# COMMAND ----------

# On serverless compute the working directory is the notebook's deployed
# directory, so ./migrations resolves to the synced migration files.
migrations_dir = Path.cwd() / "migrations"
if not migrations_dir.is_dir():
    # Fallback for interactive runs from the repo checkout.
    migrations_dir = Path(os.path.dirname(os.path.abspath("__file__"))) / "migrations"
files = sorted(migrations_dir.glob("*.sql"))
assert files, f"no migration files found under {migrations_dir}"
print(f"Found {len(files)} migration file(s) in {migrations_dir}")

# COMMAND ----------

applied, skipped = [], []
for path in files:
    migration_id = path.name
    body = path.read_text()
    checksum = hashlib.sha256(body.encode("utf-8")).hexdigest()

    cur.execute(
        "SELECT checksum FROM lakemeter.schema_migrations WHERE migration_id = %s",
        (migration_id,),
    )
    row = cur.fetchone()
    if row:
        if row[0] != checksum:
            raise RuntimeError(
                f"checksum drift on applied migration {migration_id}: "
                "edit detected after apply. Ship a new migration instead."
            )
        skipped.append(migration_id)
        continue

    try:
        cur.execute(body)
        cur.execute(
            "INSERT INTO lakemeter.schema_migrations (migration_id, checksum) VALUES (%s, %s)",
            (migration_id, checksum),
        )
        conn.commit()
        applied.append(migration_id)
    except Exception:
        conn.rollback()
        raise

print(f"Applied: {applied if applied else 'none'}")
print(f"Already applied: {skipped if skipped else 'none'}")

cur.close()
conn.close()
print("Migrations complete.")
