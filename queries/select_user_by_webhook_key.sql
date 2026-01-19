-- Authenticate user-level webhook key
-- Returns user_id for user-level operations (panic, resume)
SELECT user_id FROM user_webhook_keys WHERE key = %s;
