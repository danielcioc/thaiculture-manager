export type PaymentListItem = {
  id: string;
  booking_id: string;
  booking_code: string | null;
  customer_name: string | null;
  amount: number;
  currency: string;
  method: string;
  status: string;
  paid_at: string | null;
  due_at: string | null;
  reference: string | null;
  notes: string | null;
  booking_currency?: string | null;
  currency_matches_booking?: boolean;
  financial_error?: 'currency_mismatch' | null;
};

export type PaymentsResponse = {
  count: number;
  filters?: { status: string | null; sort_by: 'paid_at' | 'due_at'; sort_order: 'asc' | 'desc' };
  items: PaymentListItem[];
};

export type PaymentOperationsSummary = {
  currencies: Array<{
    currency: string;
    draft_count: number;
    requested_count: number;
    pending_count: number;
    paid_count: number;
    partiallypaid_count: number;
    overdue_count: number;
    cancelled_count: number;
    currency_mismatch_count: number;
    collected_amount: number;
  }>;
};
