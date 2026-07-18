export type BookingListItem = {
  id: string;
  booking_code: string;
  status: string;
  source: string;
  customer_name: string | null;
  customer_email: string | null;
  customer_country: string | null;
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
  reference: string | null;
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
    tour_name: string | null;
    pickup_location_name: string | null;
    dropoff_location_name: string | null;
    tour_date: string | null;
    pickup_time: string | null;
    total_guests: number;
    guide_language: string | null;
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
    currency: string;
  };
  assignments: Assignment[];
  operations_summary: {
    guide_cost: number;
    driver_cost: number;
    other_cost: number;
    total_cost: number;
    gross_margin: number;
    margin_percent: number;
    currency: string;
  };
};
