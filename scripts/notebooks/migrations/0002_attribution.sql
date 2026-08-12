-- 0002_attribution.sql: attribution rollup and cost-center map (W2)
CREATE TABLE IF NOT EXISTS lakemeter.attribution_daily (
    usage_date DATE NOT NULL,
    attributed_user TEXT NOT NULL,
    attribution_source TEXT NOT NULL,
    attribution_confidence TEXT NOT NULL,
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
CREATE TABLE IF NOT EXISTS lakemeter.ref_user_cost_center_map (
    user_email TEXT PRIMARY KEY,
    cost_center TEXT NOT NULL,
    department TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_attribution_date ON lakemeter.attribution_daily (usage_date);
CREATE INDEX IF NOT EXISTS idx_attribution_user_date ON lakemeter.attribution_daily (attributed_user, usage_date);
CREATE INDEX IF NOT EXISTS idx_attribution_cost_center ON lakemeter.attribution_daily (cost_center);
