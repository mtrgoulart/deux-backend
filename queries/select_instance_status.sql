SELECT 
    i.status
FROM 
    instances i
WHERE 
    i.id = %s AND i.user_id = %s;
