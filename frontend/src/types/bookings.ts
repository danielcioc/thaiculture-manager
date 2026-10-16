export type MappingStatus = 'confirmed' | 'probable_manual_review' | 'unmapped';

export type ImportReviewDecisionRequest = {
  expected_mapping_status: MappingStatus;
  expected_tour_id: string | null;
  expected_needs_manual_review: boolean;
  mapping_status: MappingStatus;
  tour_id: string | null;
  reason: string;
  confirm: boolean;
  request_id: string;
};

export type ImportReviewDecisionResponse = {
  booking_id: string;
  booking_code: string;
  status: string;
  imported_raw_tour_name: string | null;
  mapping_status: MappingStatus;
  needs_manual_review: boolean;
  tour_id: string | null;
  tour_name: string | null;
  review_event_id: string;
  replayed: boolean;
};

export type BookingListItem = {
  id: string;
  booking_code: string;
  status: string;
  source: string;
  customer_name: string | null;
  customer_email: string | null;
  customer_country: string | null;
  tour_id: string | null;
  tour_code: string | null;
  tour_name: string | null;
  tour_category: string | null;
  tour_duration_hours: number | null;
  pickup_location_name: string | null;
  pickup_location_address: string | null;
  pickup_google_maps_url: string | null;
  dropoff_location_name: string | null;
  dropoff_location_address: string | null;
  dropoff_google_maps_url: string | null;
  tour_date: string | null;
  pickup_time: string | null;
  adults: number;
  children: number;
  infants: number;
  total_guests: number;
  guide_language: string | null;
  selling_price: number;
  currency: string;
  imported_raw_tour_name: string | null;
  mapping_status: MappingStatus | null;
  needs_manual_review: boolean | null;
  created_at: string;
};

export type BookingsResponse = {
  count: number;
  items: BookingListItem[];
};

export type Payment = {
  id: string;
  amount: number;
  currency: string;
  method: string;
  status: string;
  paid_at: string | null;
  due_at: string | null;
  reference: string | null;
  notes: string | null;
};

export type Assignment = {
  id: string;
  assignment_type: string;
  guide_name: string | null;
  driver_name: string | null;
  cost: number;
  status: string;
  notes: string | null;
};

export type BookingDetailResponse = {
  booking: {
    id: string;
    booking_code: string;
    status: string;
    source: string;
    customer_name: string | null;
    customer_country: string | null;
    tour_id: string | null;
    tour_code: string | null;
    tour_name: string | null;
    pickup_location_name: string | null;
    dropoff_location_name: string | null;
    tour_date: string | null;
    pickup_time: string | null;
    total_guests: number;
    guide_language: string | null;
    imported_raw_tour_name: string | null;
    mapping_status: MappingStatus | null;
    needs_manual_review: boolean | null;
  };
  payments: Payment[];
  payment_summary: {
    selling_price: number;
    paid_amount: number;
    pending_amount: number;
    requested_amount: number;
    outstanding_amount: number;
    remaining_unrequested_amount: number;
    payment_status: string;
    booking_financial_status: string;
    currency: string;
  };
  assignments: Assignment[];
  operations_summary: {
    selling_price?: number | null;
    guide_cost: number | null;
    driver_cost: number | null;
    other_cost: number | null;
    total_cost: number | null;
    gross_margin: number | null;
    margin_percent: number | null;
    currency: string | null;
    cost_status?: string | null;
    pricing_use?: string | null;
    direct_cost_is_known?: boolean | null;
    cost_source?: string | null;
  };
};
