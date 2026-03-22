-- Fetch closed position entries with enriched buy/sell prices for commission calculation.
-- Used by commission.process task after sell price enrichment.
SELECT
    spe.id AS entry_id,
    spe.user_id,
    buy_op.execution_price AS buy_price,
    sell_op.execution_price AS sell_price,
    spe.base_qty
FROM spot_position_entries spe
JOIN operations buy_op ON spe.buy_operation_id = buy_op.id
JOIN operations sell_op ON spe.sell_operation_id = sell_op.id
WHERE spe.sell_operation_id = %s;
