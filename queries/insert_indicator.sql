INSERT INTO indicators (id, strategy_id, user_id, side, mandatory)
VALUES (%s, %s, %s, %s, %s)
ON CONFLICT (id) DO UPDATE SET mandatory = EXCLUDED.mandatory, updated_at = NOW();