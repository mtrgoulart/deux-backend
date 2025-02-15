SELECT 
    strategy_id, symbol, side, percent, condition_limit, interval
FROM strategy
WHERE user_id = %s AND strategy_id = %s;
