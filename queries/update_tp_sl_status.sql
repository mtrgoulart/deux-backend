UPDATE positions 
SET status = %s 
WHERE instance_id = %s 
AND apikey_id = %s 
AND type = %s
AND status='active';
