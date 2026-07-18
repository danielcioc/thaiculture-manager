export type InvoiceListItem = {
  id: string;
  booking_id: string;
  invoice_no: string;
  invoice_type: string;
  amount: number;
  status: string;
  issued_at: string | null;
  booking_code: string;
  booking_status: string;
  booking_source: string;
  customer_name: string | null;
  customer_email: string | null;
};

export type InvoicesResponse = {
  count: number;
  items: InvoiceListItem[];
};

export type InvoiceItem = {
  id: string;
  invoice_id: string;
  booking_id: string;
  description: string;
  qty: number;
  unit_amount: number;
  line_amount: number;
  service_date: string | null;
  booking_code: string | null;
};

export type InvoiceDetail = {
  id: string;
  booking_id: string;
  invoice_no: string;
  invoice_type: string;
  amount: number;
  status: string;
  issued_at: string | null;
  booking_code: string;
  booking_status: string;
  booking_source: string;
  customer_name: string | null;
  customer_email: string | null;
};

export type InvoiceDetailResponse = {
  invoice: InvoiceDetail;
  items: InvoiceItem[];
};
