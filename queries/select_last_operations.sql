SELECT id, date, symbol, size, side
FROM operations
WHERE instance_id=%s
AND symbol = %s
ORDER BY date DESC
LIMIT %s;