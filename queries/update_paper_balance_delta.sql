-- Apply a signed delta to a paper balance leg. Params: (delta, api_key_id, ccy).
UPDATE public.paper_balances
SET amount = amount + %s, updated_at = NOW()
WHERE api_key_id = %s AND ccy = %s;
