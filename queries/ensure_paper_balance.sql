-- Ensure a paper_balances row exists for (api_key_id, ccy) so it can be locked
-- with FOR UPDATE. No-op if it already exists. Params: (api_key_id, ccy).
INSERT INTO public.paper_balances (api_key_id, ccy, amount)
VALUES (%s, %s, 0)
ON CONFLICT (api_key_id, ccy) DO NOTHING;
