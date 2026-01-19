-- Activate panic mode for a user
-- Inserts or updates the panic state to active
INSERT INTO user_panic_state (user_id, is_panic_active, panic_activated_at, instances_stopped_json, updated_at)
VALUES (%s, TRUE, NOW(), %s, NOW())
ON CONFLICT (user_id)
DO UPDATE SET
    is_panic_active = TRUE,
    panic_activated_at = NOW(),
    instances_stopped_json = EXCLUDED.instances_stopped_json,
    updated_at = NOW();
