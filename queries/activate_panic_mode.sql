-- Activate panic mode for a user in a given environment
-- Params: (user_id, environment, instances_stopped_json)
INSERT INTO user_panic_state (user_id, environment, is_panic_active, panic_activated_at, instances_stopped_json, updated_at)
VALUES (%s, %s, TRUE, NOW(), %s, NOW())
ON CONFLICT (user_id, environment)
DO UPDATE SET
    is_panic_active = TRUE,
    panic_activated_at = NOW(),
    instances_stopped_json = EXCLUDED.instances_stopped_json,
    updated_at = NOW();
