CREATE TABLE IF NOT EXISTS spot_position_entries (
    id SERIAL PRIMARY KEY,
    operation_id INTEGER NOT NULL,
    instance_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    symbol VARCHAR(50) NOT NULL,
    base_currency VARCHAR(20) NOT NULL,
    base_qty DECIMAL(30, 12) NOT NULL,
    status VARCHAR(10) NOT NULL DEFAULT 'open',
    sell_operation_id INTEGER,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    closed_at TIMESTAMPTZ
);

-- Fast lookup for sell flow: find all open entries for an instance+user+symbol
CREATE INDEX IF NOT EXISTS idx_spe_open_lookup
ON spot_position_entries (instance_id, user_id, symbol, status)
WHERE status = 'open';

-- Lookup by operation_id (for audit/debugging)
CREATE INDEX IF NOT EXISTS idx_spe_operation ON spot_position_entries (operation_id);

-- Lookup by sell_operation_id (for P&L queries)
CREATE INDEX IF NOT EXISTS idx_spe_sell_operation ON spot_position_entries (sell_operation_id);

ALTER TABLE spot_position_entries
ADD CONSTRAINT check_base_qty_positive CHECK (base_qty > 0);

ALTER TABLE spot_position_entries
ADD CONSTRAINT check_status_valid CHECK (status IN ('open', 'closed'));
