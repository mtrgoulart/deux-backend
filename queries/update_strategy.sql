UPDATE strategy
SET percent = %s, condition_limit = %s, interval = %s,
    simultaneous_operations = %s
WHERE side = %s AND user_id = %s AND strategy_id = %s;
