SELECT type, price, status
FROM positions 
WHERE instance_id = %s AND apikey_id = %s AND status='active';
