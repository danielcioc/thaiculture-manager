export type BookingFull = {
  booking: {
    booking_code: string;
    status: string;
    source: string;
    customer_name: string | null;
    customer_email: string | null;
    customer_phone: string | null;
    customer_whatsapp: string | null;
    customer_country: string | null;
    customer_nationality: string | null;
    customer_preferred_language: string | null;
    tour_name: string | null;
    tour_category: string | null;
    tour_duration_hours: number | null;
    pickup_location_name: string | null;
    pickup_google_maps_url: string | null;
    dropoff_location_name: string | null;
    tour_date: string | null;
    pickup_time: string | null;
    adults: number | null;
    children: number | null;
    infants: number | null;
    total_guests: number | null;
    guide_language: string | null;
    selling_price: number | null;
    currency: string | null;
    created_at: string | null;
  };
  payments: Array<{
    amount: number;
    currency: string;
    method: string;
    status: string;
    paid_at: string | null;
    reference: string | null;
  }>;
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
  assignments: Array<{
    assignment_type: string;
    guide_name: string | null;
    guide_phone: string | null;
    driver_name: string | null;
    driver_phone: string | null;
    cost: number;
    status: string;
    notes: string | null;
  }>;
  operations_summary: {
    selling_price: number;
    guide_cost: number;
    driver_cost: number;
    other_cost: number;
    total_cost: number;
    gross_margin: number;
    margin_percent: number;
    currency: string;
  };
};
