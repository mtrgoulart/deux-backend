-- Migration: Create user_webhook_keys table for user-level webhook keys
-- This table stores one webhook key per user for user-level operations (panic, resume)

CREATE TABLE user_webhook_keys (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL UNIQUE REFERENCES neouser(id),
    key VARCHAR(64) NOT NULL UNIQUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_user_webhook_keys_key ON user_webhook_keys(key);
CREATE INDEX idx_user_webhook_keys_user_id ON user_webhook_keys(user_id);
