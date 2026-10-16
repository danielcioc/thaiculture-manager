export type BookingFinancialSummaryView = {
  status: string;
  total: number;
  deposit: number | null;
  paid: number;
  balance: number;
};

export function getBookingFinancialSummaryView(summary: {
  total_amount: number;
  deposit_amount: number | null;
  paid_amount: number;
  balance_due: number;
  booking_financial_status: string;
}): BookingFinancialSummaryView {
  return {
    status: summary.booking_financial_status,
    total: summary.total_amount,
    deposit: summary.deposit_amount,
    paid: summary.paid_amount,
    balance: Math.max(0, summary.balance_due),
  };
}
