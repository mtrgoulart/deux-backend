SELECT symbol, side, json_agg(row_to_json(webhook_data)) AS markets
FROM webhook_data
WHERE operation IS NULL
