UPDATE positions
SET price = ?
WHERE instance_id = ? AND api_key = ? AND type = 'SL';