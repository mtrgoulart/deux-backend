-- Deactivate panic mode for a user
-- Sets panic state to inactive and clears stopped instances
UPDATE user_panic_state
SET is_panic_active = FALSE,
    instances_stopped_json = NULL,
    updated_at = NOW()
WHERE user_id = %s;
