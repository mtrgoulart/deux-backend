SELECT
    strategy_id,
    symbol,
    side,
    percent,
    condition_limit,
    interval,
    simultaneous_operations,
    status,
    tp,
    sl
FROM
    strategy
WHERE
    user_id = %s;
