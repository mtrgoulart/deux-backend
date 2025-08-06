-- Em insert_operation.sql
INSERT INTO public.operations (user_id, api_key, symbol, side, size, price, instance_id, status, "date")
VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s);