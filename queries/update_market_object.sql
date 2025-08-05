UPDATE webhook_data
SET symbol = %s, side = %s, indicator_id = %s, operation = %s
WHERE id = %s;
