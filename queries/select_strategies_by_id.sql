SELECT
    strategy_id,
    symbol,
    side,
    percent,
    condition_limit,
    interval,
    simultaneous_operations
FROM
    strategy
WHERE
    id = %s
    AND user_id = %s;
