SELECT 
    i.api_key, i.name, k.exchange_id, i.start_date
FROM 
    instances i
JOIN 
    neouser_apikeys k ON i.api_key = k.id
WHERE 
    i.id = %s AND k.user_id = %s;
