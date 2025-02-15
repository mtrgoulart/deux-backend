SELECT 
    u.id AS api_key_id,
    u.exchange_id,
    e.name AS exchange_name,
    u.api_credentials,
    u.created_at
FROM public.neouser_apikeys u
JOIN public.exchange e ON u.exchange_id = e.id
WHERE u.user_id = %s;
