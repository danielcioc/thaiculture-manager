BEGIN;

ALTER TABLE bookings
  ADD COLUMN IF NOT EXISTS deposit_amount numeric(12,2) NULL;

COMMIT;
