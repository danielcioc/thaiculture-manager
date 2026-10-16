BEGIN;

CREATE TABLE IF NOT EXISTS website_quote_previews (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tour_id uuid NOT NULL REFERENCES tours(id),
  tour_code varchar(20) NOT NULL,
  tour_name varchar(255) NOT NULL,
  website_tour_id varchar(255) NOT NULL,
  tour_date date NOT NULL,
  adults integer NOT NULL,
  children integer NOT NULL,
  extras jsonb NOT NULL,
  currency char(3) NOT NULL,
  total numeric(12,2) NOT NULL,
  total_cost numeric(12,2) NOT NULL,
  minimum_price numeric(12,2) NOT NULL,
  rule_name varchar(100) NOT NULL,
  pricing_policy_version varchar(80) NOT NULL,
  breakdown jsonb NOT NULL,
  expires_at timestamptz NOT NULL,
  consumed_booking_id uuid REFERENCES bookings(id),
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS website_booking_idempotency (
  idempotency_key uuid PRIMARY KEY,
  payload_hash varchar(64) NOT NULL,
  booking_id uuid REFERENCES bookings(id),
  response_payload jsonb,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_website_quote_previews_expires_at
  ON website_quote_previews (expires_at);

COMMIT;
