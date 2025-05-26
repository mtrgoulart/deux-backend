INSERT INTO webhook_signals (webhook_key, symbol, side, indicator_id, instance_id, received_at)
VALUES (%s, %s, %s, %s, %s, NOW());
