SELECT id, date, symbol, size, side
FROM operations
WHERE symbol = %s
ORDER BY date DESC
LIMIT %s;