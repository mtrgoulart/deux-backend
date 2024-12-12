UPDATE public.strategy
SET status = %s, updated_at = NOW()
WHERE strategy_id = %s AND user_id = %s;