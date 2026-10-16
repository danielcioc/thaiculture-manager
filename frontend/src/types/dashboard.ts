export type DashboardSummary = {
  total_bookings: number;
  confirmed_bookings: number;
  inquiry_bookings: number;
  total_revenue: number;
  paid_revenue: number;
  pending_revenue: number;
  outstanding_revenue: number;
  total_costs: number;
  guide_costs: number;
  driver_costs: number;
  other_costs: number;
  gross_margin: number;
  margin_percent: number;
  currency: string;
  financial_kpis: {
    unpaid: number;
    depositrequested: number;
    depositpaid: number;
    partiallypaid: number;
    paid: number;
    overdue: number;
    total_outstanding: number;
  };
};
