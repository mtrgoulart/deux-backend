-- Migration: Change operations.date from timestamp to timestamptz
-- Date: 2026-02-25
-- Description:
--   The "date" column is `timestamp without time zone`. Since the PostgreSQL
--   server runs in UTC (Docker default), NOW() stores UTC values but without
--   any timezone marker. This makes dates appear 3 hours ahead when read
--   from Brazil (UTC-3).
--
--   Changing to `timestamptz` fixes this:
--   - Existing values are treated as UTC (which they are) and tagged +00
--   - PostgreSQL automatically converts to the session timezone on display
--   - Future NOW() calls store with timezone info
--
--   Before: date = 2026-02-26 00:00:36       (looks like midnight, actually 21:00 BRT)
--   After:  date = 2026-02-25 21:00:36 -0300  (correct BRT display)

-- =============================================================================
-- MIGRATION UP
-- =============================================================================

-- Convert column types. PostgreSQL needs explicit USING to tell it the
-- existing values are UTC (which they are, since NOW() ran in a UTC session).
ALTER TABLE public.operations
ALTER COLUMN "date" TYPE timestamptz USING "date" AT TIME ZONE 'UTC';

ALTER TABLE public.operations
ALTER COLUMN updated_at TYPE timestamptz USING updated_at AT TIME ZONE 'UTC';

-- =============================================================================
-- VERIFICATION
-- =============================================================================

-- Check column type changed
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'operations' AND column_name = 'date';

-- Spot check: dates should now show with timezone offset
SELECT id, "date", executed_at
FROM operations
ORDER BY id DESC
LIMIT 5;

-- =============================================================================
-- ROLLBACK (if needed)
-- =============================================================================

-- ALTER TABLE public.operations
-- ALTER COLUMN "date" TYPE timestamp USING "date" AT TIME ZONE 'UTC';
