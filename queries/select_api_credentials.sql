SELECT api_credentials
FROM public.neouser_apikeys
WHERE id = %s AND user_id = %s;
