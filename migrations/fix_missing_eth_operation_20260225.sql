-- Migration: Fix missing ETH-USDT operation and phantom operation for user_id=1
-- Date: 2026-02-25
-- Description:
--   1. Insert missing BUY operation from 19:55 BRT that was lost due to
--      varchar(5000) truncation on order_response column.
--      The order executed successfully on Binance (0.254 ETH for ~527.75 USDT)
--      but trade.save_operation failed with StringDataRightTruncation.
--   2. Create the corresponding spot_position_entry (open).
--   3. Mark operation 16002 as failed — Binance returned HTTP 400 (order below
--      minimum size: 0.08 USDT) but the code saved it as "realizada".

-- =============================================================================
-- RUN ORDER:
--   1. alter_order_response_to_text.sql   (fix column size)
--   2. fix_operations_date_timezone.sql    (fix date column type)
--   3. THIS FILE                           (fix the data)
-- =============================================================================

BEGIN;

-- Step 1: Insert the missing 19:55 BUY operation + its position entry
-- Data reconstructed from Celery ops worker logs:
--   executedQty=0.25400000, size=527.7452636 USDT, percentage=100%
--   order_response is NULL because the original was lost in the failed save
WITH inserted_op AS (
    INSERT INTO public.operations (
        user_id, api_key, symbol, side, size, order_response,
        instance_id, status, "date", executed_at
    )
    VALUES (
        1, 40, 'ETH-USDT', 'buy', 527.7452636, NULL,
        236, 'realizada',
        '2026-02-25 22:55:18+00'::timestamptz,
        '2026-02-25 22:55:18+00'::timestamptz
    )
    RETURNING id
)
INSERT INTO public.spot_position_entries (
    operation_id, instance_id, user_id, symbol,
    base_currency, base_qty, status, created_at
)
SELECT
    id,                                         -- operation_id from the insert above
    236,                                        -- instance_id
    1,                                          -- user_id
    'ETH-USDT',                                 -- symbol
    'ETH',                                      -- base_currency
    0.254000000000,                             -- base_qty (from Binance executedQty)
    'open',                                     -- status
    '2026-02-25 22:55:18+00'::timestamptz       -- created_at
FROM inserted_op;

-- Step 3: Mark the phantom operation 16002 as failed
-- Binance returned 400 Bad Request (0.08 USDT below minimum order size)
-- No actual trade was executed on the exchange
UPDATE public.operations
SET status = 'falha_api',
    order_response = '{"error": "Binance returned HTTP 400 Bad Request. Order size 0.0839866 USDT below minimum. No trade executed."}'
WHERE id = 16002
  AND user_id = 1
  AND symbol = 'ETH-USDT'
  AND status = 'realizada';

COMMIT;

-- =============================================================================
-- VERIFICATION
-- =============================================================================

-- Check the new operation was inserted
SELECT id, symbol, side, size, status, executed_at
FROM operations
WHERE user_id = 1 AND instance_id = 236 AND symbol = 'ETH-USDT'
ORDER BY date DESC
LIMIT 5;

-- Check position entry was created
SELECT id, operation_id, symbol, base_qty, status, created_at
FROM spot_position_entries
WHERE user_id = 1 AND instance_id = 236 AND symbol = 'ETH-USDT'
ORDER BY created_at DESC
LIMIT 5;

-- Verify op 16002 was updated
SELECT id, status, order_response
FROM operations
WHERE id = 16002;

-- =============================================================================
-- ROLLBACK (if needed)
-- =============================================================================

-- To rollback, you need the operation ID from step 1/2:
-- DELETE FROM spot_position_entries WHERE operation_id = <new_operation_id>;
-- DELETE FROM operations WHERE id = <new_operation_id>;
-- UPDATE operations SET status = 'realizada', order_response = NULL WHERE id = 16002;
