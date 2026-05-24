-- Deactivate panic mode for a user in a given environment
-- Params: (user_id, environment)
UPDATE user_panic_state
SET is_panic_active = FALSE,
    instances_stopped_json = NULL,
    updated_at = NOW()
WHERE user_id = %s AND environment = %s;
