-- Latest market price for a symbol from the price oracle (TimescaleDB).
-- Freshness window guards against filling at a stale price when the oracle
-- has been down. Params: (normalized_symbol, interval e.g. '5 minutes').
SELECT price
FROM market_trades
WHERE symbol = %s
  AND timestamp >= (NOW() - %s::interval)
ORDER BY timestamp DESC
LIMIT 1;
