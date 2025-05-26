SELECT
    s.id,                     -- strategy_id
    s.symbol,
    s.percent,
    s.condition_limit,
    s.interval,
    s.simultaneous_operations,
    s.tp,
    s.sl
FROM strategies s
JOIN instances i ON i.id = s.instance_id
WHERE s.side = 'buy'
  AND s.status = 1
  AND i.id = %s;
