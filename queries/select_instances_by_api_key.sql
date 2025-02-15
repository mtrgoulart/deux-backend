SELECT 
    i.id AS instance_id,
    i.api_key AS api_key_id,
    i.name AS instance_name,
    i.status AS instance_status,
    i.created_at AS instance_created_at,
    i.updated_at AS instance_updated_at,
    s.id AS strategy_id,
    s.symbol,
    s.side,
    s.percent,
    s.condition_limit,
    s.interval,
    s.simultaneous_operations
FROM instances i
JOIN instance_strategy ist ON i.id = ist.instance_id
JOIN strategy s ON ist.strategy_id = s.id
WHERE i.api_key = %s;
