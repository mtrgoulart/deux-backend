SELECT id, date, symbol, size, side
FROM operations
WHERE instance_id=%s
ORDER BY date DESC
LIMIT %s;