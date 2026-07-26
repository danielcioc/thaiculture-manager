
-- ThaiCulture Manager - Database Schema v1
-- PostgreSQL draft. Requires: CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE roles (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  name varchar(50) UNIQUE NOT NULL,
  permissions jsonb NOT NULL DEFAULT '{}'::jsonb
);

CREATE TABLE users (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  email varchar(255) UNIQUE NOT NULL,
  password_hash text NOT NULL,
  full_name varchar(255) NOT NULL,
  role_id uuid REFERENCES roles(id),
  is_active boolean DEFAULT true,
  created_at timestamptz DEFAULT now()
);

CREATE TABLE customers (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  first_name varchar(100),
  last_name varchar(100),
  display_name varchar(255) NOT NULL,
  email varchar(255),
  phone varchar(50),
  whatsapp varchar(50),
  country varchar(100),
  nationality varchar(100),
  preferred_language varchar(10) DEFAULT 'EN',
  notes text,
  created_at timestamptz DEFAULT now()
);

CREATE TABLE locations (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  name varchar(255) NOT NULL,
  address text,
  google_maps_url text,
  city varchar(100),
  country varchar(100) DEFAULT 'Thailand'
);

CREATE TABLE tours (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tour_code varchar(20) UNIQUE NOT NULL,
  name varchar(255) NOT NULL,
  category varchar(100),
  default_duration_hours numeric(4,1),
  website_url text,
  is_active boolean DEFAULT true
);

CREATE TABLE bookings (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  booking_code varchar(30) UNIQUE NOT NULL,
  status varchar(40) NOT NULL,
  source varchar(50) NOT NULL,
  customer_id uuid REFERENCES customers(id),
  tour_id uuid REFERENCES tours(id),
  tour_date date,
  pickup_time time,
  pickup_location_id uuid REFERENCES locations(id),
  dropoff_location_id uuid REFERENCES locations(id),
  adults int DEFAULT 0,
  children int DEFAULT 0,
  infants int DEFAULT 0,
  guide_language varchar(10) DEFAULT 'EN',
  selling_price numeric(12,2) DEFAULT 0,
  currency char(3) DEFAULT 'THB',
  created_by uuid REFERENCES users(id),
  created_at timestamptz DEFAULT now()
);

CREATE TABLE booking_guests (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  booking_id uuid REFERENCES bookings(id) ON DELETE CASCADE,
  full_name varchar(255) NOT NULL,
  age int,
  guest_type varchar(20),
  passport_no varchar(100),
  notes text
);

CREATE TABLE guides (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  name varchar(255) NOT NULL,
  phone varchar(50),
  line_id varchar(100),
  languages jsonb DEFAULT '[]'::jsonb,
  license_no varchar(100),
  base_area varchar(100),
  default_cost numeric(12,2) DEFAULT 0,
  rating numeric(3,2),
  notes text
);

CREATE TABLE drivers (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  name varchar(255) NOT NULL,
  phone varchar(50),
  line_id varchar(100),
  base_area varchar(100),
  default_cost numeric(12,2) DEFAULT 0,
  rating numeric(3,2)
);

CREATE TABLE vehicles (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  driver_id uuid REFERENCES drivers(id),
  vehicle_type varchar(100),
  plate_no varchar(50),
  seats int,
  insurance_valid_until date
);

CREATE TABLE suppliers (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  name varchar(255) NOT NULL,
  category varchar(100),
  contact_person varchar(255),
  phone varchar(50),
  email varchar(255),
  payment_terms text,
  cancellation_terms text
);

CREATE TABLE assignments (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  booking_id uuid REFERENCES bookings(id),
  assignment_type varchar(30) NOT NULL,
  guide_id uuid REFERENCES guides(id),
  driver_id uuid REFERENCES drivers(id),
  supplier_id uuid REFERENCES suppliers(id),
  cost numeric(12,2) DEFAULT 0,
  status varchar(40) DEFAULT 'pending',
  notes text
);

CREATE TABLE pricing_rules (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  rule_name varchar(100) NOT NULL,
  tour_id uuid REFERENCES tours(id),
  rule_type varchar(50) NOT NULL,
  conditions jsonb NOT NULL,
  calculation jsonb NOT NULL,
  is_active boolean DEFAULT true
);

CREATE TABLE pricing_quotes (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  booking_id uuid REFERENCES bookings(id),
  total_cost numeric(12,2) NOT NULL,
  recommended_price numeric(12,2) NOT NULL,
  minimum_price numeric(12,2) NOT NULL,
  final_price numeric(12,2),
  breakdown jsonb NOT NULL,
  valid_until date,
  created_at timestamptz DEFAULT now()
);

CREATE TABLE payments (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  booking_id uuid REFERENCES bookings(id),
  amount numeric(12,2) NOT NULL,
  currency char(3) DEFAULT 'THB',
  method varchar(40) NOT NULL,
  status varchar(40) NOT NULL,
  paid_at timestamptz,
  due_at timestamptz,
  received_by uuid REFERENCES users(id),
  reference varchar(255),
  notes text
);

CREATE TABLE costs (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  booking_id uuid REFERENCES bookings(id),
  cost_type varchar(50) NOT NULL,
  description varchar(255),
  amount numeric(12,2) NOT NULL,
  currency char(3) DEFAULT 'THB',
  supplier_id uuid REFERENCES suppliers(id),
  paid_status varchar(40) DEFAULT 'unpaid'
);

CREATE TABLE documents (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  booking_id uuid REFERENCES bookings(id),
  document_type varchar(50) NOT NULL,
  status varchar(40) DEFAULT 'draft',
  file_url text,
  template_version varchar(30),
  created_at timestamptz DEFAULT now()
);

CREATE TABLE invoices (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  booking_id uuid REFERENCES bookings(id),
  invoice_no varchar(50) UNIQUE NOT NULL,
  invoice_type varchar(30) NOT NULL,
  amount numeric(12,2) NOT NULL,
  status varchar(40) DEFAULT 'draft',
  issued_at timestamptz DEFAULT now()
);

CREATE TABLE receipts (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  payment_id uuid REFERENCES payments(id),
  receipt_no varchar(50) UNIQUE NOT NULL,
  issued_at timestamptz DEFAULT now(),
  document_id uuid REFERENCES documents(id)
);

CREATE TABLE emails (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  booking_id uuid REFERENCES bookings(id),
  to_email varchar(255) NOT NULL,
  subject varchar(255) NOT NULL,
  body text,
  status varchar(40) DEFAULT 'draft',
  sent_at timestamptz
);

CREATE TABLE reviews (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  booking_id uuid REFERENCES bookings(id),
  platform varchar(50),
  rating int,
  review_url text,
  requested_at timestamptz,
  received_at timestamptz
);

CREATE TABLE notifications (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  booking_id uuid REFERENCES bookings(id),
  title varchar(255) NOT NULL,
  message text,
  scheduled_at timestamptz,
  status varchar(40) DEFAULT 'pending',
  channel varchar(30) DEFAULT 'email'
);

CREATE TABLE audit_log (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid REFERENCES users(id),
  entity_type varchar(50) NOT NULL,
  entity_id uuid NOT NULL,
  action varchar(50) NOT NULL,
  old_value jsonb,
  new_value jsonb,
  created_at timestamptz DEFAULT now()
);

CREATE INDEX idx_bookings_code ON bookings(booking_code);
CREATE INDEX idx_bookings_date ON bookings(tour_date);
CREATE INDEX idx_bookings_status ON bookings(status);
CREATE INDEX idx_customers_email ON customers(email);
CREATE INDEX idx_payments_booking ON payments(booking_id);
CREATE INDEX idx_assignments_booking ON assignments(booking_id);
