-- 0003_product_coverage.sql: product-line classification and query activity (W3)
CREATE TABLE IF NOT EXISTS lakemeter.product_usage_daily (
    usage_date DATE NOT NULL,
    product_line TEXT NOT NULL,
    attributed_user TEXT NOT NULL,
    cost_center TEXT NOT NULL,
    sku_name TEXT,
    cloud TEXT,
    asset_type TEXT,
    asset_id TEXT,
    usage_unit TEXT,
    usage_quantity NUMERIC,
    list_cost NUMERIC,
    currency_code TEXT,
    record_count BIGINT,
    built_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS lakemeter.genie_query_daily (
    usage_date DATE NOT NULL,
    executed_by TEXT,
    warehouse_id TEXT,
    query_count BIGINT,
    total_duration_ms BIGINT,
    total_rows_produced BIGINT,
    ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS lakemeter.dashboard_query_daily (
    usage_date DATE NOT NULL,
    executed_by TEXT,
    warehouse_id TEXT,
    query_count BIGINT,
    total_duration_ms BIGINT,
    total_rows_produced BIGINT,
    ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_product_usage_date ON lakemeter.product_usage_daily (usage_date);
CREATE INDEX IF NOT EXISTS idx_product_usage_line_date ON lakemeter.product_usage_daily (product_line, usage_date);
CREATE INDEX IF NOT EXISTS idx_genie_query_user_date ON lakemeter.genie_query_daily (executed_by, usage_date);
CREATE INDEX IF NOT EXISTS idx_dashboard_query_user_date ON lakemeter.dashboard_query_daily (executed_by, usage_date);
