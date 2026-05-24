-- Lock the two legs of a paper fill in one statement for atomic mutation.
-- Params: (api_key_id, base_ccy, quote_ccy).
SELECT ccy, amount
FROM public.paper_balances
WHERE api_key_id = %s AND ccy IN (%s, %s)
FOR UPDATE;
