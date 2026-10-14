--
-- PostgreSQL database dump
--

\restrict uiYih0jzBNzrPKysT5qsoZqBwkTiCaTjlFneVdTBd7UsdeDzCPhEzJ7tPrshwo1

-- Dumped from database version 16.14 (Debian 16.14-1.pgdg13+1)
-- Dumped by pg_dump version 16.14 (Debian 16.14-1.pgdg13+1)

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: pgcrypto; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS pgcrypto WITH SCHEMA public;


--
-- Name: EXTENSION pgcrypto; Type: COMMENT; Schema: -; Owner: 
--

COMMENT ON EXTENSION pgcrypto IS 'cryptographic functions';


SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: assignments; Type: TABLE; Schema: public; Owner: tct_admin
--

CREATE TABLE public.assignments (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    booking_id uuid,
    assignment_type character varying(30) NOT NULL,
    guide_id uuid,
    driver_id uuid,
    supplier_id uuid,
    cost numeric(12,2) DEFAULT 0,
    status character varying(40) DEFAULT 'pending'::character varying,
    notes text
);


ALTER TABLE public.assignments OWNER TO tct_admin;

--
-- Name: audit_log; Type: TABLE; Schema: public; Owner: tct_admin
--

CREATE TABLE public.audit_log (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    user_id uuid,
    entity_type character varying(50) NOT NULL,
    entity_id uuid NOT NULL,
    action character varying(50) NOT NULL,
    old_value jsonb,
    new_value jsonb,
    created_at timestamp with time zone DEFAULT now()
);


ALTER TABLE public.audit_log OWNER TO tct_admin;

--
-- Name: booking_guests; Type: TABLE; Schema: public; Owner: tct_admin
--

CREATE TABLE public.booking_guests (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    booking_id uuid,
    full_name character varying(255) NOT NULL,
    age integer,
    guest_type character varying(20),
    passport_no character varying(100),
    notes text
);


ALTER TABLE public.booking_guests OWNER TO tct_admin;

--
-- Name: bookings; Type: TABLE; Schema: public; Owner: tct_admin
--

CREATE TABLE public.bookings (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    booking_code character varying(30) NOT NULL,
    status character varying(40) NOT NULL,
    source character varying(50) NOT NULL,
    customer_id uuid,
    tour_id uuid,
    tour_date date,
    pickup_time time without time zone,
    pickup_location_id uuid,
    dropoff_location_id uuid,
    adults integer DEFAULT 0,
    children integer DEFAULT 0,
    infants integer DEFAULT 0,
    guide_language character varying(10) DEFAULT 'EN'::character varying,
    selling_price numeric(12,2) DEFAULT 0,
    currency character(3) DEFAULT 'THB'::bpchar,
    created_by uuid,
    created_at timestamp with time zone DEFAULT now(),
    imported_raw_tour_name character varying(255),
    mapping_status character varying(30),
    needs_manual_review boolean DEFAULT false NOT NULL
);


ALTER TABLE public.bookings OWNER TO tct_admin;

--
-- Name: costs; Type: TABLE; Schema: public; Owner: tct_admin
--

CREATE TABLE public.costs (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    booking_id uuid,
    cost_type character varying(50) NOT NULL,
    description character varying(255),
    amount numeric(12,2) NOT NULL,
    currency character(3) DEFAULT 'THB'::bpchar,
    supplier_id uuid,
    paid_status character varying(40) DEFAULT 'unpaid'::character varying
);


ALTER TABLE public.costs OWNER TO tct_admin;

--
-- Name: customers; Type: TABLE; Schema: public; Owner: tct_admin
--

CREATE TABLE public.customers (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    first_name character varying(100),
    last_name character varying(100),
    display_name character varying(255) NOT NULL,
    email character varying(255),
    phone character varying(50),
    whatsapp character varying(50),
    country character varying(100),
    nationality character varying(100),
    preferred_language character varying(10) DEFAULT 'EN'::character varying,
    notes text,
    created_at timestamp with time zone DEFAULT now()
);


ALTER TABLE public.customers OWNER TO tct_admin;

--
-- Name: documents; Type: TABLE; Schema: public; Owner: tct_admin
--

CREATE TABLE public.documents (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    booking_id uuid,
    document_type character varying(50) NOT NULL,
    status character varying(40) DEFAULT 'draft'::character varying,
    file_url text,
    template_version character varying(30),
    created_at timestamp with time zone DEFAULT now()
);


ALTER TABLE public.documents OWNER TO tct_admin;

--
-- Name: drivers; Type: TABLE; Schema: public; Owner: tct_admin
--

CREATE TABLE public.drivers (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    name character varying(255) NOT NULL,
    phone character varying(50),
    line_id character varying(100),
    base_area character varying(100),
    default_cost numeric(12,2) DEFAULT 0,
    rating numeric(3,2)
);


ALTER TABLE public.drivers OWNER TO tct_admin;

--
-- Name: emails; Type: TABLE; Schema: public; Owner: tct_admin
--

CREATE TABLE public.emails (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    booking_id uuid,
    to_email character varying(255) NOT NULL,
    subject character varying(255) NOT NULL,
    body text,
    status character varying(40) DEFAULT 'draft'::character varying,
    sent_at timestamp with time zone
);


ALTER TABLE public.emails OWNER TO tct_admin;

--
-- Name: guides; Type: TABLE; Schema: public; Owner: tct_admin
--

CREATE TABLE public.guides (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    name character varying(255) NOT NULL,
    phone character varying(50),
    line_id character varying(100),
    languages jsonb DEFAULT '[]'::jsonb,
    license_no character varying(100),
    base_area character varying(100),
    default_cost numeric(12,2) DEFAULT 0,
    rating numeric(3,2),
    notes text
);


ALTER TABLE public.guides OWNER TO tct_admin;

--
-- Name: invoices; Type: TABLE; Schema: public; Owner: tct_admin
--

CREATE TABLE public.invoices (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    booking_id uuid,
    invoice_no character varying(50) NOT NULL,
    invoice_type character varying(30) NOT NULL,
    amount numeric(12,2) NOT NULL,
    status character varying(40) DEFAULT 'draft'::character varying,
    issued_at timestamp with time zone DEFAULT now()
);


ALTER TABLE public.invoices OWNER TO tct_admin;

--
-- Name: locations; Type: TABLE; Schema: public; Owner: tct_admin
--

CREATE TABLE public.locations (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    name character varying(255) NOT NULL,
    address text,
    google_maps_url text,
    city character varying(100),
    country character varying(100) DEFAULT 'Thailand'::character varying
);


ALTER TABLE public.locations OWNER TO tct_admin;

--
-- Name: notifications; Type: TABLE; Schema: public; Owner: tct_admin
--

CREATE TABLE public.notifications (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    booking_id uuid,
    title character varying(255) NOT NULL,
    message text,
    scheduled_at timestamp with time zone,
    status character varying(40) DEFAULT 'pending'::character varying,
    channel character varying(30) DEFAULT 'email'::character varying
);


ALTER TABLE public.notifications OWNER TO tct_admin;

--
-- Name: payments; Type: TABLE; Schema: public; Owner: tct_admin
--

CREATE TABLE public.payments (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    booking_id uuid,
    amount numeric(12,2) NOT NULL,
    currency character(3) DEFAULT 'THB'::bpchar,
    method character varying(40) NOT NULL,
    status character varying(40) NOT NULL,
    paid_at timestamp with time zone,
    due_at timestamp with time zone,
    received_by uuid,
    reference character varying(255),
    notes text
);


ALTER TABLE public.payments OWNER TO tct_admin;

--
-- Name: pricing_quotes; Type: TABLE; Schema: public; Owner: tct_admin
--

CREATE TABLE public.pricing_quotes (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    booking_id uuid,
    total_cost numeric(12,2) NOT NULL,
    recommended_price numeric(12,2) NOT NULL,
    minimum_price numeric(12,2) NOT NULL,
    final_price numeric(12,2),
    breakdown jsonb NOT NULL,
    valid_until date,
    created_at timestamp with time zone DEFAULT now()
);


ALTER TABLE public.pricing_quotes OWNER TO tct_admin;

--
-- Name: pricing_rules; Type: TABLE; Schema: public; Owner: tct_admin
--

CREATE TABLE public.pricing_rules (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    rule_name character varying(100) NOT NULL,
    tour_id uuid,
    rule_type character varying(50) NOT NULL,
    conditions jsonb NOT NULL,
    calculation jsonb NOT NULL,
    is_active boolean DEFAULT true
);


ALTER TABLE public.pricing_rules OWNER TO tct_admin;

--
-- Name: receipts; Type: TABLE; Schema: public; Owner: tct_admin
--

CREATE TABLE public.receipts (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    payment_id uuid,
    receipt_no character varying(50) NOT NULL,
    issued_at timestamp with time zone DEFAULT now(),
    document_id uuid
);


ALTER TABLE public.receipts OWNER TO tct_admin;

--
-- Name: reviews; Type: TABLE; Schema: public; Owner: tct_admin
--

CREATE TABLE public.reviews (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    booking_id uuid,
    platform character varying(50),
    rating integer,
    review_url text,
    requested_at timestamp with time zone,
    received_at timestamp with time zone
);


ALTER TABLE public.reviews OWNER TO tct_admin;

--
-- Name: roles; Type: TABLE; Schema: public; Owner: tct_admin
--

CREATE TABLE public.roles (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    name character varying(50) NOT NULL,
    permissions jsonb DEFAULT '{}'::jsonb NOT NULL
);


ALTER TABLE public.roles OWNER TO tct_admin;

--
-- Name: suppliers; Type: TABLE; Schema: public; Owner: tct_admin
--

CREATE TABLE public.suppliers (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    name character varying(255) NOT NULL,
    category character varying(100),
    contact_person character varying(255),
    phone character varying(50),
    email character varying(255),
    payment_terms text,
    cancellation_terms text
);


ALTER TABLE public.suppliers OWNER TO tct_admin;

--
-- Name: tours; Type: TABLE; Schema: public; Owner: tct_admin
--

CREATE TABLE public.tours (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    tour_code character varying(20) NOT NULL,
    name character varying(255) NOT NULL,
    category character varying(100),
    default_duration_hours numeric(4,1),
    website_url text,
    is_active boolean DEFAULT true
);


ALTER TABLE public.tours OWNER TO tct_admin;

--
-- Name: users; Type: TABLE; Schema: public; Owner: tct_admin
--

CREATE TABLE public.users (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    email character varying(255) NOT NULL,
    password_hash text NOT NULL,
    full_name character varying(255) NOT NULL,
    role_id uuid,
    is_active boolean DEFAULT true,
    created_at timestamp with time zone DEFAULT now()
);


ALTER TABLE public.users OWNER TO tct_admin;

--
-- Name: vehicles; Type: TABLE; Schema: public; Owner: tct_admin
--

CREATE TABLE public.vehicles (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    driver_id uuid,
    vehicle_type character varying(100),
    plate_no character varying(50),
    seats integer,
    insurance_valid_until date
);


ALTER TABLE public.vehicles OWNER TO tct_admin;

--
-- Data for Name: assignments; Type: TABLE DATA; Schema: public; Owner: tct_admin
--

COPY public.assignments (id, booking_id, assignment_type, guide_id, driver_id, supplier_id, cost, status, notes) FROM stdin;
\.


--
-- Data for Name: audit_log; Type: TABLE DATA; Schema: public; Owner: tct_admin
--

COPY public.audit_log (id, user_id, entity_type, entity_id, action, old_value, new_value, created_at) FROM stdin;
\.


--
-- Data for Name: booking_guests; Type: TABLE DATA; Schema: public; Owner: tct_admin
--

COPY public.booking_guests (id, booking_id, full_name, age, guest_type, passport_no, notes) FROM stdin;
\.


--
-- Data for Name: bookings; Type: TABLE DATA; Schema: public; Owner: tct_admin
--

COPY public.bookings (id, booking_code, status, source, customer_id, tour_id, tour_date, pickup_time, pickup_location_id, dropoff_location_id, adults, children, infants, guide_language, selling_price, currency, created_by, created_at, imported_raw_tour_name, mapping_status, needs_manual_review) FROM stdin;
8cc79cdc-06b4-43f5-8629-022cb9e77634	TCT-IMP-2026-0001	Confirmed	Imported CSV	4c43b8ea-1316-47ab-8fbe-a2c6d98f8ef6	8ea6e20a-59ba-48b1-8f90-db411c627651	2025-12-18	\N	8dc063c6-65cb-43db-a537-4823c6f27708	\N	2	0	0	EN	6500.00	THB	\N	2026-07-26 17:14:08.634824+00	Evening Ayutthaya UNESCO Temples Tour (privat)	confirmed	f
09455065-8d20-408c-80cf-7696eaaae4cb	TCT-IMP-2026-0003	Confirmed	Imported CSV	56ee69cf-dbb3-4ab0-8c11-5f77baefe749	b329e8da-62ac-4ca2-940b-2b4560e1a74b	2026-02-16	\N	6ad2f14d-44c5-4fe8-b8a8-eced9b426250	\N	5	0	0	RO	8900.00	THB	\N	2026-07-26 17:14:08.634824+00	Hua Hin Temple Tour – Cultural Day Trip	confirmed	f
79f9b3da-1f6c-4f95-8209-490cb1e8d9d0	TCT-IMP-2026-0004	Confirmed	Imported CSV	56ee69cf-dbb3-4ab0-8c11-5f77baefe749	a84c7822-5b72-4bfc-868a-099ee77d478a	2026-02-19	\N	6ad2f14d-44c5-4fe8-b8a8-eced9b426250	\N	5	0	0	RO	14000.00	THB	\N	2026-07-26 17:14:08.634824+00	Hua Hin – Bangkok Day Trip	confirmed	f
a6a4c059-5849-43c7-bbd4-e8a5da476524	TCT-IMP-2026-0005	Confirmed	Imported CSV	56ee69cf-dbb3-4ab0-8c11-5f77baefe749	6236ea5d-a905-4bd3-9b45-2e13d9fbb6eb	2026-02-22	\N	6ad2f14d-44c5-4fe8-b8a8-eced9b426250	\N	5	0	0	RO	8900.00	THB	\N	2026-07-26 17:14:08.634824+00	Kui Buri National Park – Elephant Watching	confirmed	f
4170e416-3141-4b73-9548-6fcbc19b1dde	TCT-IMP-2026-0006	Confirmed	Imported CSV	d20bbc37-ba10-4d0d-9e6a-58fd38fc1c4c	8fc4e43c-d3d4-4e27-be36-0b8d7b25d42c	2026-03-02	\N	db0c5620-45ba-4465-a2c6-b809a3d0ca04	\N	1	0	0	RO	1540.00	THB	\N	2026-07-26 17:14:08.634824+00	Ayutthaya 5 Highlights	confirmed	f
3091c4f0-b5d1-4688-996e-51f74f246ffa	TCT-IMP-2026-0009	Cancelled	Imported CSV	f31bfe20-9a96-405c-8ff7-1263437730fa	74257203-46a7-44d5-9723-fa7141ab1ea7	2026-03-14	\N	42d30815-5661-42c5-be99-8e9e72c9bf51	\N	3	0	0	FR	8900.00	THB	\N	2026-07-26 17:14:08.634824+00	Amphawa Floating Market	confirmed	f
76b03dc3-49ee-4e8c-837b-2588582c42a0	TCT-IMP-2026-0007	Confirmed	Imported CSV	d20bbc37-ba10-4d0d-9e6a-58fd38fc1c4c	b8fcf6a5-9446-4c9d-b199-ba08b3556396	2026-03-03	\N	db0c5620-45ba-4465-a2c6-b809a3d0ca04	\N	1	0	0	RO	2880.00	THB	\N	2026-07-26 17:14:08.634824+00	Khao Yai National Park – Full Day (grup)	confirmed	f
38dfd0a3-824a-4ee2-bf27-89e4db5218b9	TCT-IMP-2026-0008	Confirmed	Imported CSV	d20bbc37-ba10-4d0d-9e6a-58fd38fc1c4c	08c7024c-c888-4e0a-996f-0d68e78a5755	2026-03-04	\N	db0c5620-45ba-4465-a2c6-b809a3d0ca04	\N	1	0	0	RO	3200.00	THB	\N	2026-07-26 17:14:08.634824+00	Kanchanaburi – River Kwai + Erawan Falls (grup)	confirmed	f
ae2621e8-436c-428d-b88a-8cb0b51052ab	TCT-IMP-2026-SABRINA-TAN	Confirmed	Email	3162e671-cb5e-429e-809b-b154272d4046	8ea6e20a-59ba-48b1-8f90-db411c627651	2026-10-06	\N	\N	\N	4	0	0	EN	11500.00	THB	\N	2026-10-12 14:53:02.071197+00	Private Ayutthaya Day Trip – Relaxed Cultural Experience / Thailand Culture Tours – Private Ayutthaya Tour	confirmed	f
12bd92ea-2489-4fd1-92b0-71ae37c85f30	TCT-IMP-2026-ROMAIN-LIPPE	Confirmed	Email	fcb54c42-790c-4d0d-9540-a54dbeb7c155	74257203-46a7-44d5-9723-fa7141ab1ea7	2026-08-14	\N	\N	\N	5	0	0	FR	10500.00	THB	\N	2026-10-12 14:53:02.071197+00	Private Damnoen Saduak Floating Market & Maeklong Railway Market Tour	confirmed	f
6125d16e-3e21-4638-9c1d-549255001052	TCT-IMP-2026-0010	Confirmed	Imported CSV	a2b182e6-4492-4813-8ccc-dce04ba6e5c8	8fc4e43c-d3d4-4e27-be36-0b8d7b25d42c	2026-03-16	\N	c62071df-cd00-4ce6-b03f-31685a99d96d	\N	2	0	0	FR	8330.00	THB	\N	2026-07-26 17:14:08.634824+00	Ayutthaya UNESCO Full Day Tour (grup)	confirmed	f
dc84e49c-e0c7-4fb5-b085-b82adfdc5af0	TCT-IMP-2026-0002	Inquiry	Imported CSV	9a67aa52-1afa-47f6-ae41-d7fc44d3a930	c6bbd2ec-6531-4c02-a36b-f0fc583410f8	\N	\N	f8e41b36-e319-4b4e-b74e-b3100ffb6557	\N	4	1	0	EN	0.00	THB	\N	2026-07-26 17:14:08.634824+00	Whale Tour (nespecificat)	confirmed	f
\.


--
-- Data for Name: costs; Type: TABLE DATA; Schema: public; Owner: tct_admin
--

COPY public.costs (id, booking_id, cost_type, description, amount, currency, supplier_id, paid_status) FROM stdin;
\.


--
-- Data for Name: customers; Type: TABLE DATA; Schema: public; Owner: tct_admin
--

COPY public.customers (id, first_name, last_name, display_name, email, phone, whatsapp, country, nationality, preferred_language, notes, created_at) FROM stdin;
4c43b8ea-1316-47ab-8fbe-a2c6d98f8ef6	Alexis Chen + Holger	Roessner	Alexis Chen + Holger Roessner	Ying6789@hotmail.co.uk	\N	\N	\N	\N	EN	Plecare: 17:00 din Rojana Industrial Park | Tel. client: +65 9100 9629	2026-07-26 16:06:19.03475+00
9a67aa52-1afa-47f6-ae41-d7fc44d3a930	\N	Marina	Marina	mausm95@gmail.com	\N	\N	\N	\N	EN	\N	2026-07-26 16:06:19.03475+00
d20bbc37-ba10-4d0d-9e6a-58fd38fc1c4c	Catalina	Popa	Catalina Popa	popa.catalina01@gmail.com	\N	\N	\N	\N	RO	Plecare 10:00; taxe intrare 360 THB cash extra | Fără nr. telefon înregistrat	2026-07-26 16:06:19.03475+00
f31bfe20-9a96-405c-8ff7-1263437730fa	Élodie	Tyar	Élodie Tyar	tyar.elodie@yahoo.fr	\N	\N	\N	\N	FR	Ofertă trimisă: 8.900 THB total (2.967/pers); client a refuzat | Fără nr. telefon înregistrat	2026-07-26 16:06:19.03475+00
a2b182e6-4492-4813-8ccc-dce04ba6e5c8	Simon	Reichen	Simon Reichen	GetYourGuide: GYGZGZ5ZL3YQ	\N	\N	\N	\N	FR	Șofer: Non | Tel. șofer: +66 80 616 7489 | Ghid: Ben | Tel. ghid: +66 86 372 9833 | Rezervare GetYourGuide: GYGZGZ5ZL3YQ	2026-07-26 16:06:19.03475+00
56ee69cf-dbb3-4ab0-8c11-5f77baefe749	\N	Andreea	Barticel family	\N	\N	\N	\N	\N	RO	Tur privat	2026-07-26 16:06:19.03475+00
3162e671-cb5e-429e-809b-b154272d4046	Sabrina	Tan	Sabrina Tan Chee Yan	sabrie915@gmail.com	\N	\N	\N	\N	EN	Lead guest; booking reference 04006013	2026-10-12 14:53:02.071197+00
fcb54c42-790c-4d0d-9540-a54dbeb7c155	Romain	Lippe	Romain Lippe	romain.lippe@gmail.com	\N	\N	\N	\N	EN	Additional email: romain.lippe@ivocapital.com	2026-10-12 14:53:02.071197+00
\.


--
-- Data for Name: documents; Type: TABLE DATA; Schema: public; Owner: tct_admin
--

COPY public.documents (id, booking_id, document_type, status, file_url, template_version, created_at) FROM stdin;
\.


--
-- Data for Name: drivers; Type: TABLE DATA; Schema: public; Owner: tct_admin
--

COPY public.drivers (id, name, phone, line_id, base_area, default_cost, rating) FROM stdin;
\.


--
-- Data for Name: emails; Type: TABLE DATA; Schema: public; Owner: tct_admin
--

COPY public.emails (id, booking_id, to_email, subject, body, status, sent_at) FROM stdin;
\.


--
-- Data for Name: guides; Type: TABLE DATA; Schema: public; Owner: tct_admin
--

COPY public.guides (id, name, phone, line_id, languages, license_no, base_area, default_cost, rating, notes) FROM stdin;
\.


--
-- Data for Name: invoices; Type: TABLE DATA; Schema: public; Owner: tct_admin
--

COPY public.invoices (id, booking_id, invoice_no, invoice_type, amount, status, issued_at) FROM stdin;
c66c36d5-7524-417c-ab70-72a17c4ac527	ae2621e8-436c-428d-b88a-8cb0b51052ab	TCT-INV-2026-1006-001	final	11500.00	issued	2026-09-22 17:00:00+00
34c1042a-0a35-4158-934b-ce784bf9d556	12bd92ea-2489-4fd1-92b0-71ae37c85f30	TCT-INV-2026-0807-001	final	10500.00	issued	2026-08-06 17:00:00+00
\.


--
-- Data for Name: locations; Type: TABLE DATA; Schema: public; Owner: tct_admin
--

COPY public.locations (id, name, address, google_maps_url, city, country) FROM stdin;
8dc063c6-65cb-43db-a537-4823c6f27708	SO/ Bangkok Hotel	\N	\N	SO/ Bangkok Hotel	Thailand
f8e41b36-e319-4b4e-b74e-b3100ffb6557	Cerere (fără răspuns)	\N	\N	Cerere (fără răspuns)	Thailand
6ad2f14d-44c5-4fe8-b8a8-eced9b426250	Hua Hin	\N	\N	Hua Hin	Thailand
db0c5620-45ba-4465-a2c6-b809a3d0ca04	The Raweekanlaya Bangkok	\N	\N	The Raweekanlaya Bangkok	Thailand
42d30815-5661-42c5-be99-8e9e72c9bf51	Let's Zzz Bangkok	\N	\N	Let's Zzz Bangkok	Thailand
c62071df-cd00-4ce6-b03f-31685a99d96d	Bangkok	\N	\N	Bangkok	Thailand
\.


--
-- Data for Name: notifications; Type: TABLE DATA; Schema: public; Owner: tct_admin
--

COPY public.notifications (id, booking_id, title, message, scheduled_at, status, channel) FROM stdin;
\.


--
-- Data for Name: payments; Type: TABLE DATA; Schema: public; Owner: tct_admin
--

COPY public.payments (id, booking_id, amount, currency, method, status, paid_at, due_at, received_by, reference, notes) FROM stdin;
9632782a-4731-4ce2-808c-d724262fabdc	ae2621e8-436c-428d-b88a-8cb0b51052ab	11500.00	THB	Bank transfer	Paid	2026-09-22 17:00:00+00	\N	\N	04006013	Full payment; date supplied by user. Final invoice: TCT-Final-Invoice-2026-1006-04006013-Sabrina-Tan.pdf.
cc57aec5-f61a-4b2f-804a-4ddd8ab15eb8	12bd92ea-2489-4fd1-92b0-71ae37c85f30	10500.00	THB	Bank transfer	Paid	2026-08-06 17:00:00+00	\N	\N	TCT-INV-2026-0807-001	Full payment confirmed by email on 2026-08-07. Bank transfer recorded per user instruction; original correspondence mentioned Revolut/PayPal.
1bc12f08-f7db-47b7-b479-1109e557534e	8cc79cdc-06b4-43f5-8629-022cb9e77634	6500.00	THB	Cash	Paid	2025-12-18 05:00:00+00	\N	\N	TCT-TH-2025-1218-001	Cash paid directly to guide on tour date; confirmed by Daniel
\.


--
-- Data for Name: pricing_quotes; Type: TABLE DATA; Schema: public; Owner: tct_admin
--

COPY public.pricing_quotes (id, booking_id, total_cost, recommended_price, minimum_price, final_price, breakdown, valid_until, created_at) FROM stdin;
\.


--
-- Data for Name: pricing_rules; Type: TABLE DATA; Schema: public; Owner: tct_admin
--

COPY public.pricing_rules (id, rule_name, tour_id, rule_type, conditions, calculation, is_active) FROM stdin;
3f31a3a0-f46b-4a99-84af-ac8c24660eb8	PRICE-WEB-007-V1	8fc4e43c-d3d4-4e27-be36-0b8d7b25d42c	private_total	{"currency": "THB", "tour_code": "WEB-007", "max_guests": 4, "min_guests": 4, "source_note": "Private Ayutthaya Day Trip 2026-10-06, 4 guests, THB 11500 total", "group_size_basis": "per_booking", "confidence_status": "confirmed"}	{"excludes": "Lunch, drinks, personal expenses and gratuities", "includes": "Driver, private premium van, fuel, tolls, parking, temple entrance fees, insurance and VAT", "vat_rate": 0.07, "guide_cost": 2500.00, "cost_status": "available", "pricing_use": "approved_for_quote", "vehicle_cost": 3000.00, "entrance_cost": 800.00, "insurance_cost": 300.00, "insurance_rule": "4 guests + 1 driver + 1 guide", "direct_cost_total": 6600.00, "selling_price_net": 10747.66, "selling_price_gross": 11500.00, "requires_manual_review": false}	t
a669792d-8a07-483c-abc7-a429b921a5a3	PRICE-WEB-028-V1	08c7024c-c888-4e0a-996f-0d68e78a5755	group_per_person	{"currency": "THB", "tour_code": "WEB-028", "max_guests": 1, "min_guests": 1, "source_note": "Group record 2026-03-04, THB 3200 per person reference", "group_size_basis": "per_person", "confidence_status": "estimated"}	{"excludes": "Pending structured inclusions/exclusions review", "includes": "Historical group price reference", "vat_rate": 0.07, "cost_status": "incomplete", "pricing_use": "reference_only", "insurance_rule": "needs_review", "direct_cost_total": null, "selling_price_net": 2990.65, "selling_price_gross": 3200.00, "requires_manual_review": true}	t
68c71d94-fb76-43a6-843f-b1414d09582e	PRICE-WEB-027-V1	b8fcf6a5-9446-4c9d-b199-ba08b3556396	group_per_person	{"currency": "THB", "tour_code": "WEB-027", "max_guests": 1, "min_guests": 1, "source_note": "Group record 2026-03-03, THB 2880 per person reference", "group_size_basis": "per_person", "confidence_status": "estimated"}	{"excludes": "Pending structured inclusions/exclusions review", "includes": "Historical group price reference", "vat_rate": 0.07, "cost_status": "incomplete", "pricing_use": "reference_only", "insurance_rule": "needs_review", "direct_cost_total": null, "selling_price_net": 2691.59, "selling_price_gross": 2880.00, "requires_manual_review": true}	t
703afdd0-c043-48df-a05e-0748cc90a145	PRICE-WEB-023-V1	b329e8da-62ac-4ca2-940b-2b4560e1a74b	private_total	{"currency": "THB", "tour_code": "WEB-023", "max_guests": 5, "min_guests": 5, "source_note": "Private tour 2026-02-16, 5 guests, THB 8900 total, supplier cost THB 5000", "group_size_basis": "per_booking", "confidence_status": "estimated"}	{"excludes": "Entrance fees and meals", "includes": "Vehicle, driver, fuel, tolls, parking, guide assistance, insurance, drinking water and hotel pickup/drop-off", "vat_rate": 0.07, "cost_status": "available", "pricing_use": "reference_only", "insurance_rule": "guests_plus_driver_plus_guide", "direct_cost_total": 5000.00, "selling_price_net": 8317.76, "selling_price_gross": 8900.00, "requires_manual_review": true}	t
525c5794-8a52-4f72-8cec-b37633c27140	PRICE-WEB-006-V1	8ea6e20a-59ba-48b1-8f90-db411c627651	private_total	{"currency": "THB", "tour_code": "WEB-006", "max_guests": 4, "min_guests": 1, "source_note": "Historical private booking, 2 guests, THB 6500 total", "group_size_basis": "per_booking", "confidence_status": "estimated"}	{"excludes": "Pending review", "includes": "Private evening Ayutthaya tour; inclusions pending standardization", "vat_rate": 0.07, "guide_cost": null, "cost_status": "incomplete", "pricing_use": "reference_only", "vehicle_cost": null, "entrance_cost": null, "insurance_cost": null, "insurance_rule": "guests_plus_driver_plus_guide", "direct_cost_total": null, "selling_price_net": 6074.77, "selling_price_gross": 6500.00, "requires_manual_review": true}	t
a53b8326-c87f-465c-b529-4ece48d77cce	PRICE-WEB-021-V1	a84c7822-5b72-4bfc-868a-099ee77d478a	private_total	{"currency": "THB", "tour_code": "WEB-021", "max_guests": 5, "min_guests": 5, "source_note": "Private tour 2026-02-19, 5 guests, THB 14000 total, supplier cost THB 6200", "group_size_basis": "per_booking", "confidence_status": "estimated"}	{"excludes": "Entrance fees and meals", "includes": "Vehicle, driver, fuel, tolls, parking, guide assistance, insurance, drinking water and hotel pickup/drop-off", "vat_rate": 0.07, "cost_status": "available", "pricing_use": "reference_only", "insurance_rule": "guests_plus_driver_plus_guide", "direct_cost_total": 6200.00, "selling_price_net": 13084.11, "selling_price_gross": 14000.00, "requires_manual_review": true}	t
a05eaa15-0acc-4798-9e40-3f256fcf9ab4	PRICE-WEB-022-V1	6236ea5d-a905-4bd3-9b45-2e13d9fbb6eb	private_total	{"currency": "THB", "tour_code": "WEB-022", "max_guests": 5, "min_guests": 5, "source_note": "Private tour 2026-02-22, 5 guests, THB 8900 total, supplier cost THB 6550", "group_size_basis": "per_booking", "confidence_status": "estimated"}	{"excludes": "Entrance fees and meals", "includes": "4x4 safari vehicle with ranger, private van, driver, guide assistance, insurance, water and hotel transfers", "vat_rate": 0.07, "cost_status": "available", "pricing_use": "reference_only", "insurance_rule": "guests_plus_driver_plus_guide", "direct_cost_total": 6550.00, "selling_price_net": 8317.76, "selling_price_gross": 8900.00, "requires_manual_review": true}	t
\.


--
-- Data for Name: receipts; Type: TABLE DATA; Schema: public; Owner: tct_admin
--

COPY public.receipts (id, payment_id, receipt_no, issued_at, document_id) FROM stdin;
\.


--
-- Data for Name: reviews; Type: TABLE DATA; Schema: public; Owner: tct_admin
--

COPY public.reviews (id, booking_id, platform, rating, review_url, requested_at, received_at) FROM stdin;
\.


--
-- Data for Name: roles; Type: TABLE DATA; Schema: public; Owner: tct_admin
--

COPY public.roles (id, name, permissions) FROM stdin;
\.


--
-- Data for Name: suppliers; Type: TABLE DATA; Schema: public; Owner: tct_admin
--

COPY public.suppliers (id, name, category, contact_person, phone, email, payment_terms, cancellation_terms) FROM stdin;
\.


--
-- Data for Name: tours; Type: TABLE DATA; Schema: public; Owner: tct_admin
--

COPY public.tours (id, tour_code, name, category, default_duration_hours, website_url, is_active) FROM stdin;
c76334d5-9123-4454-822f-53773aeae3e4	WEB-001	9 Wonders of the Capital	Website Canonical Tour	8.0	9-wonders-of-capital.html	t
d3c2f12a-ef1b-4a1d-822c-b2b1b78fbcbf	WEB-002	The City of Moon and Sapphires	Website Canonical Tour	8.0	orasul-lunii-safirelor.html	t
889dac27-b6ef-4225-a08e-96c99dac451f	WEB-003	Classic Bangkok	Website Canonical Tour	8.0	classic-bangkok-tour.html	t
db575168-36f6-4110-ba20-41f030e88984	WEB-004	Mystic Bangkok	Website Canonical Tour	8.0	mystic-bangkok-tour.html	t
c67f07c1-beae-43df-9504-60dc91374b89	WEB-005	All of Bangkok (Extended Tour)	Website Canonical Tour	8.0	all-bangkok-tour.html	t
8ea6e20a-59ba-48b1-8f90-db411c627651	WEB-006	Evening in Ayutthaya	Website Canonical Tour	8.0	evening-in-ayutthaya.html	t
8fc4e43c-d3d4-4e27-be36-0b8d7b25d42c	WEB-007	Ayutthaya: 5 Essential Sights	Website Canonical Tour	8.0	ayutthaya-5-sights-tour.html	t
41e45333-b66b-412b-a273-050c811216b5	WEB-008	Evening in Ancient Siam	Website Canonical Tour	8.0	evening-in-ancient-siam.html	t
38adf687-34ae-4c9c-9fc1-e81eb92df05c	WEB-009	Dragon's Lair	Website Canonical Tour	8.0	dragons-lair-tour.html	t
d3a91ba1-46db-4098-ae87-783d91a383fe	WEB-010	Jurassic Park Tour	Website Canonical Tour	8.0	jurassic-park-tour.html	t
4f9153d1-1d45-4c6e-a6d2-7eaa6e55248a	WEB-011	Wat Khun Chan & Ko Kret	Website Canonical Tour	8.0	wat-khun-chan-ko-kret.html	t
74257203-46a7-44d5-9723-fa7141ab1ea7	WEB-012	Amphawa: The City on Water	Website Canonical Tour	8.0	amphawa-extended-tour.html	t
c3d20e1b-5096-435b-8b04-219d46a50f9b	WEB-013	Pattaya Night Tour	Website Canonical Tour	4.0	pattaya-night-tour.html	t
7b5f579b-d1fe-45e1-82bc-b26125dfe838	WEB-014	Baan Sukhawadee	Website Canonical Tour	4.0	baan-sukhawadee-tour.html	t
804ecaca-6561-41a9-aaad-cdb4bfe664e7	WEB-015	Treasure of Isan	Website Canonical Tour	16.0	treasure-of-isan-tour.html	t
c6bbd2ec-6531-4c02-a36b-f0fc583410f8	WEB-016	Whale Safari	Website Canonical Tour	16.0	whale-safari-tour.html	t
ff6ced76-2535-46dc-adc0-38b66c2215bb	WEB-017	Above The Clouds	Website Canonical Tour	16.0	above-the-clouds-tour.html	t
53de53ba-bf32-489f-88af-5c7ab7a2ea42	WEB-018	Explorers Expedition	Website Canonical Tour	16.0	explorers-expedition-tour.html	t
eea5709e-0792-4409-9c3d-e4c6a00af3a2	WEB-019	Amazing Thailand + Cultural Depths	Website Canonical Tour	24.0	amazing-thailand-ritual.html	t
69dc7f42-edf9-4d98-b58a-357708491805	WEB-020	Phuket: Explorer’s Day Out	Website Canonical Tour	8.0	phuket-tour.html	t
a84c7822-5b72-4bfc-868a-099ee77d478a	WEB-021	1-Day Trip – Hua Hin → Bangkok	Website Canonical Tour	8.0	hua-hin-bangkok-day-trip.html	t
6236ea5d-a905-4bd3-9b45-2e13d9fbb6eb	WEB-022	Elephant Watching in Kui Buri National Park	Website Canonical Tour	8.0	kui-buri-elephant-watching.html	t
b329e8da-62ac-4ca2-940b-2b4560e1a74b	WEB-023	Hua Hin Temple Tour	Website Canonical Tour	8.0	hua-hin-temple-tour.html	t
fae041e8-9446-43fd-ac71-a71951d6f090	WEB-024	Chiang Rai: White Temple, Blue Temple & Hill Tribe Village – day trip	Website Canonical Tour	8.0	chiang-rai-white-blue-temples.html	t
dd81a181-da5f-4828-9d0e-6f9d7404a9f7	WEB-025	Hua Hin Temples & Elephant Safari	Website Canonical Tour	8.0	hua-hin-temples-elephants-safari.html	t
004b4cae-7a88-489c-9ad5-b05680734f4c	WEB-026	Uthai Thani Sacred River & Hidden Heritage	Website Canonical Tour	16.0	uthai-thani-sacred-river-hidden-heritage.html	t
b8fcf6a5-9446-4c9d-b199-ba08b3556396	WEB-027	Khao Yai National Park – Full Day	Nature & Wildlife	10.0	\N	t
08c7024c-c888-4e0a-996f-0d68e78a5755	WEB-028	Kanchanaburi: River Kwai & Erawan Falls	History & Nature	12.0	\N	t
\.


--
-- Data for Name: users; Type: TABLE DATA; Schema: public; Owner: tct_admin
--

COPY public.users (id, email, password_hash, full_name, role_id, is_active, created_at) FROM stdin;
\.


--
-- Data for Name: vehicles; Type: TABLE DATA; Schema: public; Owner: tct_admin
--

COPY public.vehicles (id, driver_id, vehicle_type, plate_no, seats, insurance_valid_until) FROM stdin;
\.


--
-- Name: assignments assignments_pkey; Type: CONSTRAINT; Schema: public; Owner: tct_admin
--

ALTER TABLE ONLY public.assignments
    ADD CONSTRAINT assignments_pkey PRIMARY KEY (id);


--
-- Name: audit_log audit_log_pkey; Type: CONSTRAINT; Schema: public; Owner: tct_admin
--

ALTER TABLE ONLY public.audit_log
    ADD CONSTRAINT audit_log_pkey PRIMARY KEY (id);


--
-- Name: booking_guests booking_guests_pkey; Type: CONSTRAINT; Schema: public; Owner: tct_admin
--

ALTER TABLE ONLY public.booking_guests
    ADD CONSTRAINT booking_guests_pkey PRIMARY KEY (id);


--
-- Name: bookings bookings_booking_code_key; Type: CONSTRAINT; Schema: public; Owner: tct_admin
--

ALTER TABLE ONLY public.bookings
    ADD CONSTRAINT bookings_booking_code_key UNIQUE (booking_code);


--
-- Name: bookings bookings_pkey; Type: CONSTRAINT; Schema: public; Owner: tct_admin
--

ALTER TABLE ONLY public.bookings
    ADD CONSTRAINT bookings_pkey PRIMARY KEY (id);


--
-- Name: costs costs_pkey; Type: CONSTRAINT; Schema: public; Owner: tct_admin
--

ALTER TABLE ONLY public.costs
    ADD CONSTRAINT costs_pkey PRIMARY KEY (id);


--
-- Name: customers customers_pkey; Type: CONSTRAINT; Schema: public; Owner: tct_admin
--

ALTER TABLE ONLY public.customers
    ADD CONSTRAINT customers_pkey PRIMARY KEY (id);


--
-- Name: documents documents_pkey; Type: CONSTRAINT; Schema: public; Owner: tct_admin
--

ALTER TABLE ONLY public.documents
    ADD CONSTRAINT documents_pkey PRIMARY KEY (id);


--
-- Name: drivers drivers_pkey; Type: CONSTRAINT; Schema: public; Owner: tct_admin
--

ALTER TABLE ONLY public.drivers
    ADD CONSTRAINT drivers_pkey PRIMARY KEY (id);


--
-- Name: emails emails_pkey; Type: CONSTRAINT; Schema: public; Owner: tct_admin
--

ALTER TABLE ONLY public.emails
    ADD CONSTRAINT emails_pkey PRIMARY KEY (id);


--
-- Name: guides guides_pkey; Type: CONSTRAINT; Schema: public; Owner: tct_admin
--

ALTER TABLE ONLY public.guides
    ADD CONSTRAINT guides_pkey PRIMARY KEY (id);


--
-- Name: invoices invoices_invoice_no_key; Type: CONSTRAINT; Schema: public; Owner: tct_admin
--

ALTER TABLE ONLY public.invoices
    ADD CONSTRAINT invoices_invoice_no_key UNIQUE (invoice_no);


--
-- Name: invoices invoices_pkey; Type: CONSTRAINT; Schema: public; Owner: tct_admin
--

ALTER TABLE ONLY public.invoices
    ADD CONSTRAINT invoices_pkey PRIMARY KEY (id);


--
-- Name: locations locations_pkey; Type: CONSTRAINT; Schema: public; Owner: tct_admin
--

ALTER TABLE ONLY public.locations
    ADD CONSTRAINT locations_pkey PRIMARY KEY (id);


--
-- Name: notifications notifications_pkey; Type: CONSTRAINT; Schema: public; Owner: tct_admin
--

ALTER TABLE ONLY public.notifications
    ADD CONSTRAINT notifications_pkey PRIMARY KEY (id);


--
-- Name: payments payments_pkey; Type: CONSTRAINT; Schema: public; Owner: tct_admin
--

ALTER TABLE ONLY public.payments
    ADD CONSTRAINT payments_pkey PRIMARY KEY (id);


--
-- Name: pricing_quotes pricing_quotes_pkey; Type: CONSTRAINT; Schema: public; Owner: tct_admin
--

ALTER TABLE ONLY public.pricing_quotes
    ADD CONSTRAINT pricing_quotes_pkey PRIMARY KEY (id);


--
-- Name: pricing_rules pricing_rules_pkey; Type: CONSTRAINT; Schema: public; Owner: tct_admin
--

ALTER TABLE ONLY public.pricing_rules
    ADD CONSTRAINT pricing_rules_pkey PRIMARY KEY (id);


--
-- Name: receipts receipts_pkey; Type: CONSTRAINT; Schema: public; Owner: tct_admin
--

ALTER TABLE ONLY public.receipts
    ADD CONSTRAINT receipts_pkey PRIMARY KEY (id);


--
-- Name: receipts receipts_receipt_no_key; Type: CONSTRAINT; Schema: public; Owner: tct_admin
--

ALTER TABLE ONLY public.receipts
    ADD CONSTRAINT receipts_receipt_no_key UNIQUE (receipt_no);


--
-- Name: reviews reviews_pkey; Type: CONSTRAINT; Schema: public; Owner: tct_admin
--

ALTER TABLE ONLY public.reviews
    ADD CONSTRAINT reviews_pkey PRIMARY KEY (id);


--
-- Name: roles roles_name_key; Type: CONSTRAINT; Schema: public; Owner: tct_admin
--

ALTER TABLE ONLY public.roles
    ADD CONSTRAINT roles_name_key UNIQUE (name);


--
-- Name: roles roles_pkey; Type: CONSTRAINT; Schema: public; Owner: tct_admin
--

ALTER TABLE ONLY public.roles
    ADD CONSTRAINT roles_pkey PRIMARY KEY (id);


--
-- Name: suppliers suppliers_pkey; Type: CONSTRAINT; Schema: public; Owner: tct_admin
--

ALTER TABLE ONLY public.suppliers
    ADD CONSTRAINT suppliers_pkey PRIMARY KEY (id);


--
-- Name: tours tours_pkey; Type: CONSTRAINT; Schema: public; Owner: tct_admin
--

ALTER TABLE ONLY public.tours
    ADD CONSTRAINT tours_pkey PRIMARY KEY (id);


--
-- Name: tours tours_tour_code_key; Type: CONSTRAINT; Schema: public; Owner: tct_admin
--

ALTER TABLE ONLY public.tours
    ADD CONSTRAINT tours_tour_code_key UNIQUE (tour_code);


--
-- Name: users users_email_key; Type: CONSTRAINT; Schema: public; Owner: tct_admin
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_email_key UNIQUE (email);


--
-- Name: users users_pkey; Type: CONSTRAINT; Schema: public; Owner: tct_admin
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (id);


--
-- Name: vehicles vehicles_pkey; Type: CONSTRAINT; Schema: public; Owner: tct_admin
--

ALTER TABLE ONLY public.vehicles
    ADD CONSTRAINT vehicles_pkey PRIMARY KEY (id);


--
-- Name: idx_assignments_booking; Type: INDEX; Schema: public; Owner: tct_admin
--

CREATE INDEX idx_assignments_booking ON public.assignments USING btree (booking_id);


--
-- Name: idx_bookings_code; Type: INDEX; Schema: public; Owner: tct_admin
--

CREATE INDEX idx_bookings_code ON public.bookings USING btree (booking_code);


--
-- Name: idx_bookings_date; Type: INDEX; Schema: public; Owner: tct_admin
--

CREATE INDEX idx_bookings_date ON public.bookings USING btree (tour_date);


--
-- Name: idx_bookings_status; Type: INDEX; Schema: public; Owner: tct_admin
--

CREATE INDEX idx_bookings_status ON public.bookings USING btree (status);


--
-- Name: idx_customers_email; Type: INDEX; Schema: public; Owner: tct_admin
--

CREATE INDEX idx_customers_email ON public.customers USING btree (email);


--
-- Name: idx_payments_booking; Type: INDEX; Schema: public; Owner: tct_admin
--

CREATE INDEX idx_payments_booking ON public.payments USING btree (booking_id);


--
-- Name: assignments assignments_booking_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: tct_admin
--

ALTER TABLE ONLY public.assignments
    ADD CONSTRAINT assignments_booking_id_fkey FOREIGN KEY (booking_id) REFERENCES public.bookings(id);


--
-- Name: assignments assignments_driver_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: tct_admin
--

ALTER TABLE ONLY public.assignments
    ADD CONSTRAINT assignments_driver_id_fkey FOREIGN KEY (driver_id) REFERENCES public.drivers(id);


--
-- Name: assignments assignments_guide_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: tct_admin
--

ALTER TABLE ONLY public.assignments
    ADD CONSTRAINT assignments_guide_id_fkey FOREIGN KEY (guide_id) REFERENCES public.guides(id);


--
-- Name: assignments assignments_supplier_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: tct_admin
--

ALTER TABLE ONLY public.assignments
    ADD CONSTRAINT assignments_supplier_id_fkey FOREIGN KEY (supplier_id) REFERENCES public.suppliers(id);


--
-- Name: audit_log audit_log_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: tct_admin
--

ALTER TABLE ONLY public.audit_log
    ADD CONSTRAINT audit_log_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: booking_guests booking_guests_booking_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: tct_admin
--

ALTER TABLE ONLY public.booking_guests
    ADD CONSTRAINT booking_guests_booking_id_fkey FOREIGN KEY (booking_id) REFERENCES public.bookings(id) ON DELETE CASCADE;


--
-- Name: bookings bookings_created_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: tct_admin
--

ALTER TABLE ONLY public.bookings
    ADD CONSTRAINT bookings_created_by_fkey FOREIGN KEY (created_by) REFERENCES public.users(id);


--
-- Name: bookings bookings_customer_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: tct_admin
--

ALTER TABLE ONLY public.bookings
    ADD CONSTRAINT bookings_customer_id_fkey FOREIGN KEY (customer_id) REFERENCES public.customers(id);


--
-- Name: bookings bookings_dropoff_location_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: tct_admin
--

ALTER TABLE ONLY public.bookings
    ADD CONSTRAINT bookings_dropoff_location_id_fkey FOREIGN KEY (dropoff_location_id) REFERENCES public.locations(id);


--
-- Name: bookings bookings_pickup_location_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: tct_admin
--

ALTER TABLE ONLY public.bookings
    ADD CONSTRAINT bookings_pickup_location_id_fkey FOREIGN KEY (pickup_location_id) REFERENCES public.locations(id);


--
-- Name: bookings bookings_tour_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: tct_admin
--

ALTER TABLE ONLY public.bookings
    ADD CONSTRAINT bookings_tour_id_fkey FOREIGN KEY (tour_id) REFERENCES public.tours(id);


--
-- Name: costs costs_booking_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: tct_admin
--

ALTER TABLE ONLY public.costs
    ADD CONSTRAINT costs_booking_id_fkey FOREIGN KEY (booking_id) REFERENCES public.bookings(id);


--
-- Name: costs costs_supplier_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: tct_admin
--

ALTER TABLE ONLY public.costs
    ADD CONSTRAINT costs_supplier_id_fkey FOREIGN KEY (supplier_id) REFERENCES public.suppliers(id);


--
-- Name: documents documents_booking_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: tct_admin
--

ALTER TABLE ONLY public.documents
    ADD CONSTRAINT documents_booking_id_fkey FOREIGN KEY (booking_id) REFERENCES public.bookings(id);


--
-- Name: emails emails_booking_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: tct_admin
--

ALTER TABLE ONLY public.emails
    ADD CONSTRAINT emails_booking_id_fkey FOREIGN KEY (booking_id) REFERENCES public.bookings(id);


--
-- Name: invoices invoices_booking_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: tct_admin
--

ALTER TABLE ONLY public.invoices
    ADD CONSTRAINT invoices_booking_id_fkey FOREIGN KEY (booking_id) REFERENCES public.bookings(id);


--
-- Name: notifications notifications_booking_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: tct_admin
--

ALTER TABLE ONLY public.notifications
    ADD CONSTRAINT notifications_booking_id_fkey FOREIGN KEY (booking_id) REFERENCES public.bookings(id);


--
-- Name: payments payments_booking_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: tct_admin
--

ALTER TABLE ONLY public.payments
    ADD CONSTRAINT payments_booking_id_fkey FOREIGN KEY (booking_id) REFERENCES public.bookings(id);


--
-- Name: payments payments_received_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: tct_admin
--

ALTER TABLE ONLY public.payments
    ADD CONSTRAINT payments_received_by_fkey FOREIGN KEY (received_by) REFERENCES public.users(id);


--
-- Name: pricing_quotes pricing_quotes_booking_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: tct_admin
--

ALTER TABLE ONLY public.pricing_quotes
    ADD CONSTRAINT pricing_quotes_booking_id_fkey FOREIGN KEY (booking_id) REFERENCES public.bookings(id);


--
-- Name: pricing_rules pricing_rules_tour_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: tct_admin
--

ALTER TABLE ONLY public.pricing_rules
    ADD CONSTRAINT pricing_rules_tour_id_fkey FOREIGN KEY (tour_id) REFERENCES public.tours(id);


--
-- Name: receipts receipts_document_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: tct_admin
--

ALTER TABLE ONLY public.receipts
    ADD CONSTRAINT receipts_document_id_fkey FOREIGN KEY (document_id) REFERENCES public.documents(id);


--
-- Name: receipts receipts_payment_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: tct_admin
--

ALTER TABLE ONLY public.receipts
    ADD CONSTRAINT receipts_payment_id_fkey FOREIGN KEY (payment_id) REFERENCES public.payments(id);


--
-- Name: reviews reviews_booking_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: tct_admin
--

ALTER TABLE ONLY public.reviews
    ADD CONSTRAINT reviews_booking_id_fkey FOREIGN KEY (booking_id) REFERENCES public.bookings(id);


--
-- Name: users users_role_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: tct_admin
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_role_id_fkey FOREIGN KEY (role_id) REFERENCES public.roles(id);


--
-- Name: vehicles vehicles_driver_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: tct_admin
--

ALTER TABLE ONLY public.vehicles
    ADD CONSTRAINT vehicles_driver_id_fkey FOREIGN KEY (driver_id) REFERENCES public.drivers(id);


--
-- PostgreSQL database dump complete
--

\unrestrict uiYih0jzBNzrPKysT5qsoZqBwkTiCaTjlFneVdTBd7UsdeDzCPhEzJ7tPrshwo1

