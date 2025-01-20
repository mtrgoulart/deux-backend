INSERT INTO public.operations (date, symbol, size, side, price, status, instance_id)
VALUES (%s, %s, %s, %s, %s, %s, %s)
RETURNING id;