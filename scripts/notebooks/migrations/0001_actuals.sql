-- 0001_actuals.sql: actual usage ingestion tables (W1)
CREATE TABLE IF NOT EXISTS lakemeter.actuals_usage_daily (
    usage_date DATE NOT NULL,
    record_id TEXT,
    record_type TEXT,
    account_id TEXT,
    workspace_id TEXT,
    sku_name TEXT,
    cloud TEXT,
    usage_start_time TIMESTAMPTZ,
    usage_end_time TIMESTAMPTZ,
    usage_unit TEXT,
    usage_quantity NUMERIC,
    list_price NUMERIC,
    list_cost NUMERIC,
    currency_code TEXT,
    custom_tags JSONB,
    run_as TEXT,
    owned_by TEXT,
    created_by TEXT,
    warehouse_id TEXT,
    endpoint_id TEXT,
    endpoint_name TEXT,
    cluster_id TEXT,
    job_id TEXT,
    dlt_pipeline_id TEXT,
    node_type TEXT,
    ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS lakemeter.actuals_ingestion_state (
    pipeline_name TEXT PRIMARY KEY,
    watermark_date DATE,
    last_run_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_status TEXT,
    last_error TEXT
);
CREATE INDEX IF NOT EXISTS idx_actuals_date ON lakemeter.actuals_usage_daily (usage_date);
CREATE INDEX IF NOT EXISTS idx_actuals_sku ON lakemeter.actuals_usage_daily (sku_name);
CREATE INDEX IF NOT EXISTS idx_actuals_run_as ON lakemeter.actuals_usage_daily (run_as);
CREATE INDEX IF NOT EXISTS idx_actuals_ws_date ON lakemeter.actuals_usage_daily (workspace_id, usage_date);
