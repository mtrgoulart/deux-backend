UPDATE webhook_data
SET symbol = %s, side = %s, indicator = %s, operation = %s
WHERE id = %s;
