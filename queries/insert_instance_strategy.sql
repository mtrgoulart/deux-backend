-- Insert na tabela de relação instance_strategy
INSERT INTO public.instance_strategy (
    instance_id, strategy_id
) VALUES (
    %s, %s
);
