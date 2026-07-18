import type { PaymentsResponse } from '../types/payments';
import { formatCurrency, formatDateTime } from '../utils/formatters';
import { getStatusClass } from '../utils/status';
import { DetailItem, SectionHeader, StatCard } from './ui';

type PaymentsListProps = {
  data: PaymentsResponse;
};

export function PaymentsList({ data }: PaymentsListProps) {
  const paidCount = data.items.filter(
    (item) => item.status.toLowerCase() === 'paid',
  ).length;
  const pendingCount = data.items.filter(
    (item) => item.status.toLowerCase().includes('pending'),
  ).length;
  const totalAmount = data.items.reduce(
    (sum, item) => sum + Number(item.amount || 0),
    0,
  );
  const currency = data.items[0]?.currency ?? 'THB';

  return (
    <>
      <div className="grid">
        <StatCard label="Total Payments" value={data.count} />

        <StatCard label="Paid" value={paidCount} />

        <StatCard label="Pending" value={pendingCount} />

        <StatCard label="Total Amount" value={formatCurrency(totalAmount, currency)} />
      </div>

      <section className="panel">
        <SectionHeader
          title="Payments"
          subtitle="Financial transactions overview"
          pill={
            <span className={`meta-pill ${getStatusClass(pendingCount > 0 ? 'pending' : 'paid')}`}>
              {paidCount} Paid
            </span>
          }
        />

        {data.items.length === 0 ? (
          <p>No payments found.</p>
        ) : (
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
                  <span className={`status ${getStatusClass(payment.status)}`}>
                    {payment.status}
                  </span>
                </div>

                <div className="payment-page-grid">
                  <DetailItem label="Method" value={payment.method || '-'} />

                  <DetailItem label="Paid At" value={formatDateTime(payment.paid_at)} />

                  <DetailItem label="Reference" value={payment.reference || '-'} />
                </div>
              </article>
            ))}
          </div>
        )}
      </section>
    </>
  );
}
