
-----------------------------------------------------
--Resultado por custo acumulado
WITH sell_operations AS (
    SELECT 
        id,
        date,
        symbol,
        size * price AS sell_value,
        ROW_NUMBER() OVER (PARTITION BY symbol ORDER BY date) AS sell_order
    FROM 
        operations o
    WHERE 
        price <> 0 
        AND status = 'realizada'
        AND side = 'sell'
),
buy_operations AS (
    SELECT 
        date,
        symbol,
        SUM(size) AS total_size
    FROM 
        operations o
    WHERE 
        price <> 0 
        AND status = 'realizada'
        AND side = 'buy'
    GROUP BY 
        date, symbol
),
sell_with_cumulative_costs AS (
    SELECT 
        s1.id,
        s1.date AS sell_date,
        s1.symbol,
        s1.sell_value,
        s1.sell_order,
        SUM(b.total_size) AS buy_cost
    FROM 
        sell_operations s1
    LEFT JOIN buy_operations b
        ON s1.symbol = b.symbol
        AND b.date > COALESCE((
            SELECT MAX(date)
            FROM sell_operations s2
            WHERE s2.symbol = s1.symbol AND s2.sell_order = s1.sell_order - 1
        ), '1900-01-01')
        AND b.date <= s1.date
    GROUP BY 
        s1.id, s1.date, s1.symbol, s1.sell_value, s1.sell_order
)
SELECT id
,sell_date
,symbol
,sell_value
,sell_order
,buy_cost
,sell_value-buy_cost as profit
,sum(sum(sell_value-buy_cost)) over (partition by symbol order by sell_date) as profitAcumullative
FROM sell_with_cumulative_costs
group by id
,sell_date
,symbol
,sell_value
,sell_order
,buy_cost
ORDER BY symbol, sell_order

-----------------------------------------------------
--Estrategias por usuario 
select i.id 
,i.name as instance_name
,n.username as creator
,s.symbol 
,s.side 
,s.status 
,s.created_at
,s.condition_limit 
,s.simultaneous_operations 
from INSTANCES i
join instance_strategy i_s
on i_s.instance_id =i.id
join strategy s 
on s.id =i_s.strategy_id 
join neouser n
on n.id =i.user_id
where n.id=6


select i.id as instance_id
,i.name as instance_name
,n.username as creator
,s.symbol 
,s.side 
,s.status 
,s.created_at
,s.condition_limit 
,s."interval" 
,i.status 
from INSTANCES i
join instance_strategy i_s
on i_s.instance_id =i.id
join strategy s 
on s.id =i_s.strategy_id 
join neouser n
on n.id =i.user_id
where n.id=6


update operations 
set price=0.714
where id=1447

SELECT o.id,
            o.date,
            o.side,
            o.symbol,
            o.price,
            o.size,
            COALESCE(NULLIF(o.price, 0),
                (
                    SELECT hp.price
                    FROM hourly_prices hp
                    WHERE hp.symbol = o.symbol
                    AND DATE_TRUNC('hour', hp.date) = DATE_TRUNC('hour', o.date)
                    LIMIT 1
                )
            ) as price_adjust,
            o.size * COALESCE(NULLIF(o.price, 0),
                (
                    SELECT hp.price
                    FROM hourly_prices hp
                    WHERE hp.symbol = o.symbol
                    AND DATE_TRUNC('hour', hp.date) = DATE_TRUNC('hour', o.date)
                    LIMIT 1
                )
            ) AS sell_value,
            row_number() OVER (PARTITION BY o.symbol ORDER BY o.date) AS sell_order
           FROM operations o
          where symbol='AVAX-USDT' 
and date>='2025-03-20'
order by "date" desc

delete from operations where id=1731

update operations set date='2025-03-23 01:35:32.632' where id=2698

select * from operations
where symbol='ETH-USDT' 
and date>='2025-03-20'
order by "date" desc

select * from hourly_prices where symbol='BTC-USDT' order by date desc

select * from operations where smbol='ADA-USDT' order by "date" desc



select * from okx_operations oo 