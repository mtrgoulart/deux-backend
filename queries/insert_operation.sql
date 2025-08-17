INSERT INTO public.operations (user_id, api_key, symbol, side, size, oreder_response, instance_id, status, "date")
VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
RETURNING id;