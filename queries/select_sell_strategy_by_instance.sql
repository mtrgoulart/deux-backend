SELECT
    s.id,   
    s.symbol,
    s.percent,
    s.condition_limit,
    s.interval,
    s.simultaneous_operations,
    s.tp,
    s.sl
FROM
    instance_strategy AS ist
JOIN
    strategy AS s ON ist.strategy_id = s.id
WHERE
    ist.instance_id = %s
    AND s.side='sell';