-- Signal Pipeline Tracing
-- Tracks the lifecycle of each webhook signal through the processing pipeline.
-- Each signal gets one row; stages are accumulated in the JSONB array.

CREATE TABLE IF NOT EXISTS signal_traces (
    id              SERIAL PRIMARY KEY,
    trace_id        VARCHAR(32) NOT NULL UNIQUE,
    pattern         VARCHAR(20) NOT NULL,
    signal_key_suffix VARCHAR(8),
    user_id         INTEGER,
    instance_id     INTEGER,
    symbol          VARCHAR(30),
    side            VARCHAR(20),
    current_stage   VARCHAR(40) DEFAULT 'webhook_received',
    final_status    VARCHAR(20) DEFAULT 'in_progress',
    stages          JSONB NOT NULL DEFAULT '[]'::jsonb,
    error_message   TEXT,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW(),
    completed_at    TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_signal_traces_trace_id ON signal_traces (trace_id);
CREATE INDEX IF NOT EXISTS idx_signal_traces_created_at ON signal_traces (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_signal_traces_user_id ON signal_traces (user_id);
CREATE INDEX IF NOT EXISTS idx_signal_traces_instance_id ON signal_traces (instance_id);
CREATE INDEX IF NOT EXISTS idx_signal_traces_final_status ON signal_traces (final_status);
CREATE INDEX IF NOT EXISTS idx_signal_traces_stages ON signal_traces USING GIN (stages);
