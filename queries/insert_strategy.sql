INSERT INTO public.strategy (
    user_id, strategy_id, symbol, side, percent, condition_limit, interval, simultaneous_operations, status
) VALUES (
    %s, %s, %s, %s, %s, %s, %s, %s, %s
);
