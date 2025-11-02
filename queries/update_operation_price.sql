UPDATE operations
SET 
    execution_price = %s,
    executed_at = %s::timestamptz
WHERE id = %s;