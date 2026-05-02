-- Migration: Virtual Operations + Virtual Position Entries
-- Date: 2026-04-30
-- Description:
--   Adds two new tables that mirror the real operations + spot_position_entries
--   schema, but represent strategy-level signal records rather than executed
--   trades on an exchange. Used to compute strategy % return independent of
--   whether the owner actually executed the signal.
--
--   Key differences from real schema:
--     - No `size`, `api_key`, `order_response`, `executed_at` (size-independent)
--     - `execution_price` is populated asynchronously by the price enrichment
--       task — may be NULL until enriched (or permanently if all sources fail).
--     - `signal_trace_id` ties back to signal_traces for audit.
--     - `base_qty` always 1 on virtual_position_entries (size-independent;
--        % return cancels qty out of the math).

BEGIN;

-- =============================================================================
-- virtual_operations
-- =============================================================================
CREATE TABLE IF NOT EXISTS virtual_operations (
    id                       SERIAL PRIMARY KEY,
    date                     TIMESTAMPTZ NOT NULL,
    symbol                   VARCHAR(50) NOT NULL,
    side                     VARCHAR(10) NOT NULL,
    execution_price          NUMERIC(30, 12),
    status                   VARCHAR(30) NOT NULL DEFAULT 'pending',
    instance_id              INTEGER NOT NULL,
    user_id                  INTEGER NOT NULL,           -- instance owner
    signal_trace_id          VARCHAR(32),
    price_enrichment_error   TEXT,
    created_at               TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at               TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_virtual_op_side   CHECK (side IN ('buy', 'sell')),
    CONSTRAINT chk_virtual_op_status CHECK (status IN ('pending', 'priced', 'enrichment_failed'))
);

CREATE INDEX IF NOT EXISTS idx_vop_instance_date
    ON virtual_operations (instance_id, date DESC);

CREATE INDEX IF NOT EXISTS idx_vop_status_pending
    ON virtual_operations (status)
    WHERE status = 'pending';

CREATE INDEX IF NOT EXISTS idx_vop_signal_trace
    ON virtual_operations (signal_trace_id);

-- =============================================================================
-- virtual_position_entries
-- =============================================================================
CREATE TABLE IF NOT EXISTS virtual_position_entries (
    id                  SERIAL PRIMARY KEY,
    operation_id        INTEGER NOT NULL REFERENCES virtual_operations(id),
    instance_id         INTEGER NOT NULL,
    user_id             INTEGER NOT NULL,            -- instance owner
    symbol              VARCHAR(50) NOT NULL,
    base_currency       VARCHAR(20) NOT NULL,
    base_qty            DECIMAL(30, 12) NOT NULL DEFAULT 1,
    status              VARCHAR(10) NOT NULL DEFAULT 'open',
    sell_operation_id   INTEGER REFERENCES virtual_operations(id),
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    closed_at           TIMESTAMPTZ,
    CONSTRAINT chk_virtual_pos_status   CHECK (status IN ('open', 'closed')),
    CONSTRAINT chk_virtual_pos_base_qty CHECK (base_qty > 0)
);

-- FIFO match index: find oldest open entry for a given instance+symbol
CREATE INDEX IF NOT EXISTS idx_vpe_open_fifo
    ON virtual_position_entries (instance_id, symbol, created_at)
    WHERE status = 'open';

CREATE INDEX IF NOT EXISTS idx_vpe_operation
    ON virtual_position_entries (operation_id);

CREATE INDEX IF NOT EXISTS idx_vpe_sell_operation
    ON virtual_position_entries (sell_operation_id);

CREATE INDEX IF NOT EXISTS idx_vpe_instance_status
    ON virtual_position_entries (instance_id, status);

COMMIT;
