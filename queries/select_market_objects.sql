SELECT symbol, side, json_agg(row_to_json(webhook_data)) AS markets
FROM webhook_data
WHERE instance_id=%s
AND symbol = %s
AND side = %s
AND created_at >= %s 
AND operation_task_id IS NULL
GROUP BY symbol, side
