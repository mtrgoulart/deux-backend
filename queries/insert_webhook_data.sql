INSERT INTO public.webhook_data (
    key,
    symbol,
    side,
    indicator_id,
    instance_id
)
VALUES (%s, %s, %s, %s, %s);
