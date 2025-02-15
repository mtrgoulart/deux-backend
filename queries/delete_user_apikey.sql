DELETE FROM public.neouser_apikeys
WHERE user_id = %s AND exchange_id = %s;
