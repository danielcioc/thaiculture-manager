-- Add importer review metadata without changing existing booking rows.
BEGIN;

ALTER TABLE bookings
  ADD COLUMN IF NOT EXISTS imported_raw_tour_name text NULL,
  ADD COLUMN IF NOT EXISTS mapping_status varchar(40) NULL,
  ADD COLUMN IF NOT EXISTS needs_manual_review boolean NULL;

COMMIT;
