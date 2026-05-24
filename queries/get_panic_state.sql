-- Get the panic state for a user in a given environment
-- Params: (user_id, environment)
-- Returns: user_id, is_panic_active, panic_activated_at, instances_stopped_json
SELECT user_id, is_panic_active, panic_activated_at, instances_stopped_json
FROM user_panic_state
WHERE user_id = %s AND environment = %s;
