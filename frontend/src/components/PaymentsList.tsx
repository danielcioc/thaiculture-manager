import type { PaymentOperationsSummary, PaymentsResponse } from '../types/payments';
import { formatCurrency, formatDateTime } from '../utils/formatters';
import { getStatusClass } from '../utils/status';
import { DetailItem, SectionHeader, StatCard } from './ui';

type PaymentsListProps = {
  data: PaymentsResponse | null;
  summary: PaymentOperationsSummary | null;
  loading: boolean;
  error: string;
  statusFilter: string;
  sortBy: 'paid_at' | 'due_at';
  sortOrder: 'asc' | 'desc';
  onStatusFilterChange: (value: string) => void;
  onSortChange: (sortBy: 'paid_at' | 'due_at', sortOrder: 'asc' | 'desc') => void;
};

const statuses = [
  ['all', 'All statuses'], ['draft', 'Draft'], ['requested', 'Requested'],
  ['pending', 'Pending'], ['paid', 'Paid'], ['partiallypaid', 'Partially paid'],
  ['overdue', 'Overdue'], ['cancelled', 'Cancelled'],
];

export function PaymentsList({
  data, summary, loading, error, statusFilter, sortBy, sortOrder,
  onStatusFilterChange, onSortChange,
}: PaymentsListProps) {
  const totals = summary?.currencies ?? [];
  const statusCounts = totals.reduce<Record<string, number>>((acc, item) => ({
    draft: (acc.draft ?? 0) + item.draft_count,
    requested: (acc.requested ?? 0) + item.requested_count,
    pending: (acc.pending ?? 0) + item.pending_count,
    paid: (acc.paid ?? 0) + item.paid_count,
    partiallypaid: (acc.partiallypaid ?? 0) + item.partiallypaid_count,
    overdue: (acc.overdue ?? 0) + item.overdue_count,
    cancelled: (acc.cancelled ?? 0) + item.cancelled_count,
  }), {});
  const mismatchCount = totals.reduce((sum, item) => sum + item.currency_mismatch_count, 0);

  return (
    <>
      <div className="grid">
        <StatCard label="Payments shown" value={data?.count ?? 0} />
        {totals.map((item) => (
          <StatCard key={item.currency} label={`Collected (${item.currency})`} value={formatCurrency(item.collected_amount, item.currency)} />
        ))}
        <StatCard label="Currency mismatches" value={mismatchCount} />
      </div>

      <section className="panel">
        <SectionHeader
          title="Payments"
          subtitle="Collected totals exclude cancelled, draft, invalid, non-positive, and currency-mismatched records."
          pill={<span className="meta-pill">{Object.values(statusCounts).reduce((sum, count) => sum + count, 0)} payments across all statuses</span>}
        />

        <div className="payment-controls">
          <label>Payment status
            <select value={statusFilter} onChange={(event) => onStatusFilterChange(event.target.value)}>
              {statuses.map(([value, label]) => <option key={value} value={value}>{label}</option>)}
            </select>
          </label>
          <label>Sort date
            <select value={sortBy} onChange={(event) => onSortChange(event.target.value as 'paid_at' | 'due_at', sortOrder)}>
              <option value="paid_at">Paid date</option>
              <option value="due_at">Due date</option>
            </select>
          </label>
          <label>Order
            <select value={sortOrder} onChange={(event) => onSortChange(sortBy, event.target.value as 'asc' | 'desc')}>
              <option value="desc">Newest first</option>
              <option value="asc">Oldest first</option>
            </select>
          </label>
        </div>

        {error && <p role="alert">Unable to load payments: {error}</p>}
        {mismatchCount > 0 && <p className="financial-error" role="alert">{mismatchCount} payment(s) use a different currency from their booking and are excluded from financial totals.</p>}
        {loading && <p role="status">Loading payments...</p>}
        {!loading && data?.items.length === 0 ? (
          <p>No payments found for this filter.</p>
        ) : !loading && data ? (
          <div className="payments-list-page">
            {data.items.map((payment) => (
              <article className="payment-row interactive-card" key={payment.id}>
                <div className="payment-row-top">
                  <div>
                    <div className="payment-name">{formatCurrency(payment.amount, payment.currency)}</div>
                    <div className="payment-secondary">
                      {payment.booking_code || 'No booking code'} · {payment.customer_name || 'No customer'}
                    </div>
                  </div>
                  <span className={`status ${getStatusClass(payment.status)}`}>{payment.status}</span>
                </div>

                <div className="payment-page-grid">
                  <DetailItem label="Method" value={payment.method || '-'} />
                  <DetailItem label="Paid At" value={formatDateTime(payment.paid_at)} />
                  <DetailItem label="Due At" value={formatDateTime(payment.due_at)} />
                  <DetailItem label="Reference" value={payment.reference || '-'} />
                  <DetailItem label="Notes" value={payment.notes || '-'} />
                </div>
                {payment.financial_error === 'currency_mismatch' && (
                  <p className="financial-error" role="alert">Currency mismatch: excluded from collected and booking totals.</p>
                )}
              </article>
            ))}
          </div>
        ) : null}
      </section>
    </>
  );
}
