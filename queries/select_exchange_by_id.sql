SELECT oficial_exchange, name, base_url, is_demo
FROM public.exchange
WHERE id = %s;
