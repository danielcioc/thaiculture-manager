import type { DashboardSummary } from '../types/dashboard';

export function dashboardFinancialCards(summary: DashboardSummary) {
  const kpis = summary.financial_kpis;
  return [
    { key: 'unpaid', label: 'Unpaid', value: kpis.unpaid, definition: 'Bookings with no valid paid or open payment.' },
    { key: 'depositrequested', label: 'Deposit requested', value: kpis.depositrequested, definition: 'Bookings with an open requested, pending, or overdue payment and no confirmed payment.' },
    { key: 'depositpaid', label: 'Deposit paid', value: kpis.depositpaid, definition: 'Bookings whose confirmed payments cover the configured deposit, below the total.' },
    { key: 'partiallypaid', label: 'Partially paid', value: kpis.partiallypaid, definition: 'Bookings with confirmed payments below the total and not classified as deposit paid.' },
    { key: 'paid', label: 'Paid', value: kpis.paid, definition: 'Bookings whose valid same-currency confirmed payments cover the total.' },
    { key: 'overdue', label: 'Overdue', value: kpis.overdue, definition: 'Bookings with an overdue open payment and a remaining balance.' },
    { key: 'total_outstanding', label: 'Total outstanding', value: kpis.total_outstanding, definition: 'Sum of balance due across all bookings; not filtered by operational status.' },
  ];
}
