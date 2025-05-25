SELECT 
    i.api_key, i.name, k.exchange_id, i.start_date,is2.id
FROM 
    instances i
JOIN 
    neouser_apikeys k ON i.api_key = k.id
left join instance_sharing is2 
on is2.instance_id =i.id
WHERE 
    i.id = %s AND k.user_id = %s;