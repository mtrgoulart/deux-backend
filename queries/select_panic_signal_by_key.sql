-- Resolve a panic/resume webhook key to its user, environment, and bound action.
-- Returns: user_id, environment, action
SELECT user_id, environment, action
FROM user_panic_signals
WHERE key = %s;
