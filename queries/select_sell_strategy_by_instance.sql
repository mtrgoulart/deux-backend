SELECT
    s.id,
    i.symbol,
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
join instances i on i.id =ist.instance_id
WHERE
    ist.instance_id = %s
    AND s.side='sell';