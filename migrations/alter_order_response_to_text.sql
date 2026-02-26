-- Migration: Change order_response column from varchar(5000) to TEXT
-- Date: 2026-02-25
-- Description: The varchar(5000) limit causes StringDataRightTruncation errors
--              when Binance responses contain many fills (large fills array).
--              Changing to TEXT removes the size constraint.

-- =============================================================================
-- MIGRATION UP
-- =============================================================================

ALTER TABLE public.operations
ALTER COLUMN order_response TYPE TEXT;

-- =============================================================================
-- VERIFICATION
-- =============================================================================

SELECT
    column_name,
    data_type,
    character_maximum_length
FROM information_schema.columns
WHERE table_name = 'operations'
  AND column_name = 'order_response';

-- =============================================================================
-- ROLLBACK (if needed)
-- =============================================================================

-- To rollback (will fail if any row exceeds 5000 chars):
-- ALTER TABLE public.operations
-- ALTER COLUMN order_response TYPE VARCHAR(5000);
