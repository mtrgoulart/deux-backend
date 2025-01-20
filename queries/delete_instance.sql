DELETE FROM instances
WHERE id = %s AND EXISTS (
    SELECT 1 FROM neouser_apikeys a
    WHERE a.id = instances.api_key AND a.user_id = %s
);
