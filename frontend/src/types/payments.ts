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
};

export type PaymentsResponse = {
  count: number;
  items: PaymentListItem[];
};
