-- Migration: Add Flat Value Sizing Support to Strategy Table
-- Date: 2025-12-08
-- Description: Adds size_mode and flat_value columns to support both percentage and flat value sizing modes

-- =============================================================================
-- MIGRATION UP
-- =============================================================================

-- Add size_mode column (defaults to 'percentage' for backward compatibility)
ALTER TABLE strategy
ADD COLUMN IF NOT EXISTS size_mode VARCHAR(20) DEFAULT 'percentage';

-- Add flat_value column (used when size_mode = 'flat_value')
ALTER TABLE strategy
ADD COLUMN IF NOT EXISTS flat_value DECIMAL(20, 8) DEFAULT NULL;

-- Add check constraint to ensure flat_value is positive when set
ALTER TABLE strategy
ADD CONSTRAINT IF NOT EXISTS check_flat_value_positive
CHECK (flat_value IS NULL OR flat_value > 0);

-- Add check constraint to ensure size_mode is valid
ALTER TABLE strategy
ADD CONSTRAINT IF NOT EXISTS check_size_mode_valid
CHECK (size_mode IN ('percentage', 'flat_value'));

-- Add comment to size_mode column
COMMENT ON COLUMN strategy.size_mode IS 'Sizing mode: "percentage" (default) or "flat_value"';

-- Add comment to flat_value column
COMMENT ON COLUMN strategy.flat_value IS 'Exact dollar amount to trade when size_mode is "flat_value"';

-- =============================================================================
-- VERIFICATION QUERIES
-- =============================================================================

-- Verify columns were added
SELECT
    column_name,
    data_type,
    column_default,
    is_nullable
FROM information_schema.columns
WHERE table_name = 'strategy'
  AND column_name IN ('size_mode', 'flat_value')
ORDER BY ordinal_position;

-- Verify constraints were added
SELECT
    constraint_name,
    constraint_type
FROM information_schema.table_constraints
WHERE table_name = 'strategy'
  AND constraint_name IN ('check_flat_value_positive', 'check_size_mode_valid');

-- Check existing strategies (should all default to 'percentage' mode)
SELECT
    id,
    side,
    percent,
    size_mode,
    flat_value
FROM strategy
LIMIT 10;

-- =============================================================================
-- ROLLBACK (if needed)
-- =============================================================================

-- To rollback this migration, run:
-- ALTER TABLE strategy DROP CONSTRAINT IF EXISTS check_size_mode_valid;
-- ALTER TABLE strategy DROP CONSTRAINT IF EXISTS check_flat_value_positive;
-- ALTER TABLE strategy DROP COLUMN IF EXISTS flat_value;
-- ALTER TABLE strategy DROP COLUMN IF EXISTS size_mode;

-- =============================================================================
-- NOTES
-- =============================================================================

-- 1. This migration is NON-BREAKING:
--    - All existing strategies will default to size_mode = 'percentage'
--    - Existing code continues to work without changes
--
-- 2. After migration:
--    - Existing strategies continue using percentage-based sizing
--    - New strategies can use either 'percentage' or 'flat_value' mode
--
-- 3. Validation:
--    - flat_value must be positive when set
--    - size_mode must be 'percentage' or 'flat_value'
--
-- 4. Usage examples:
--
--    -- Create percentage-based strategy (legacy mode)
--    INSERT INTO strategy (side, percent, size_mode, flat_value)
--    VALUES ('buy', 0.10, 'percentage', NULL);
--
--    -- Create flat value strategy (new mode)
--    INSERT INTO strategy (side, percent, size_mode, flat_value)
--    VALUES ('buy', 0.0, 'flat_value', 500.00);
