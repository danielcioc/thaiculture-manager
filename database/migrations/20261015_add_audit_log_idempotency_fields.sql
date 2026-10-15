-- Add idempotency and actor snapshots for future audit-log review events.
-- Existing generic audit rows remain valid; this migration does not backfill.
BEGIN;

ALTER TABLE audit_log
  ADD COLUMN IF NOT EXISTS request_id uuid NULL,
  ADD COLUMN IF NOT EXISTS request_payload_hash varchar(64) NULL,
  ADD COLUMN IF NOT EXISTS actor_email_snapshot text NULL,
  ADD COLUMN IF NOT EXISTS actor_name_snapshot text NULL,
  ADD COLUMN IF NOT EXISTS reason text NULL;

CREATE UNIQUE INDEX IF NOT EXISTS uq_audit_log_user_request_id
  ON audit_log (user_id, request_id)
  WHERE request_id IS NOT NULL;

COMMIT;
