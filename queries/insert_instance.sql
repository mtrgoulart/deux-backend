INSERT INTO instances (user_id, api_key, name, status, created_at, updated_at,instance_uuid)
VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP,%s)
RETURNING id;