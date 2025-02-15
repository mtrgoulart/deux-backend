SELECT id, strategy_id, side, mandatory
FROM indicators
WHERE strategy_id = %s AND side = %s AND user_id = %s;