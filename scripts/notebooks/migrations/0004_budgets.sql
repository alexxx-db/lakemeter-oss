-- 0004_budgets.sql: budget definitions and alert records (W4)
CREATE TABLE IF NOT EXISTS lakemeter.ref_budgets (
    scope_type TEXT NOT NULL,
    scope_key TEXT NOT NULL,
    monthly_budget NUMERIC NOT NULL,
    warn_pct NUMERIC DEFAULT 0.8,
    critical_pct NUMERIC DEFAULT 1.0,
    active BOOLEAN DEFAULT TRUE,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (scope_type, scope_key)
);
CREATE TABLE IF NOT EXISTS lakemeter.budget_alerts (
    alert_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    alert_month DATE NOT NULL,
    scope_type TEXT NOT NULL,
    scope_key TEXT NOT NULL,
    mtd_cost NUMERIC,
    monthly_budget NUMERIC,
    severity TEXT NOT NULL,
    raised_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_budget_alerts_month ON lakemeter.budget_alerts (alert_month);
