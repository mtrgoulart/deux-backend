-- Single-currency paper balance. Params: (api_key_id, ccy).
SELECT amount
FROM public.paper_balances
WHERE api_key_id = %s AND ccy = %s;
