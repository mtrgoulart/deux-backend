-- Get the panic state for a user
-- Returns: user_id, is_panic_active, panic_activated_at, instances_stopped_json
SELECT user_id, is_panic_active, panic_activated_at, instances_stopped_json
FROM user_panic_state
WHERE user_id = %s;
