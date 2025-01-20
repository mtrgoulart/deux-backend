SELECT 
    id,
    date,
    symbol,
    size,
    side,
    price,
    status
FROM 
    operations
WHERE 
    instance_id = %s;
