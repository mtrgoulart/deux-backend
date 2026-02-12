SELECT
    e_official.name AS official_name,
    e.name,
    e.base_url,
    e.is_demo
FROM public.exchange e
JOIN public.exchange e_official ON e_official.id = e.oficial_exchange
WHERE e.id = %s;
