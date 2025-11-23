INSERT INTO public.operations (user_id, api_key, symbol, side, size, order_response, instance_id, status, "date",executed_at)
VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW(),%s)
RETURNING id;