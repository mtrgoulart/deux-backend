SELECT
    s.id,
    s.strategy_id AS strategy_uuid,
    s.symbol,
    s.side,
    s.percent,
    s.condition_limit,
    s.interval,
    s.simultaneous_operations,
    s.status,
    s.tp,
    s.sl
FROM
    instance_strategy AS ist
JOIN
    strategy AS s ON ist.strategy_id = s.id
WHERE
    ist.instance_id = %s;