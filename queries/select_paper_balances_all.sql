-- All paper balances for an api key. Params: (api_key_id,).
SELECT ccy, amount
FROM public.paper_balances
WHERE api_key_id = %s
ORDER BY ccy;
