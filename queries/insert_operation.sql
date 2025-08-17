INSERT INTO public.operations (user_id, api_key, symbol, side, size, order_response, instance_id, status, "date")
VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW())
RETURNING id;