ALTER TABLE neouser_sharing
  ADD COLUMN IF NOT EXISTS size_mode VARCHAR(20) NOT NULL DEFAULT 'percentage';
