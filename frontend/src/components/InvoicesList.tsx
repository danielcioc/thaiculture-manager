import type { InvoicesResponse } from '../types/invoices';
import { formatCurrency, formatDate } from '../utils/formatters';
import { getStatusClass } from '../utils/status';

type InvoicesListProps = {
  data: InvoicesResponse;
  onSelectInvoice: (invoiceNo: string) => void;
};

export function InvoicesList({ data, onSelectInvoice }: InvoicesListProps) {
  const totalAmount = data.items.reduce(
    (sum, item) => sum + Number(item.amount || 0),
    0,
  );

  return (
    <>
      <div className="grid">
        <div className="card">
          <span>Total Invoices</span>
          <strong>{data.items.length}</strong>
        </div>

        <div className="card">
          <span>Issued</span>
          <strong>{data.items.filter((item) => item.status === 'Issued').length}</strong>
        </div>

        <div className="card">
          <span>Total Amount</span>
          <strong>{formatCurrency(totalAmount, 'THB')}</strong>
        </div>
      </div>

      <section className="panel">
        <div className="section-header">
          <div>
            <h2 style={{ margin: 0 }}>Invoices</h2>
            <p className="section-subtitle">Billing overview</p>
          </div>
          <span className="meta-pill">{data.count} total</span>
        </div>

        {data.items.length === 0 ? (
          <p>No invoices found.</p>
        ) : (
          <div className="booking-list">
            {data.items.map((invoice) => (
              <button
                type="button"
                className="booking-row interactive-card"
                key={invoice.id}
                onClick={() => onSelectInvoice(invoice.invoice_no)}
              >
                <div className="booking-row-top">
                  <div>
                    <div className="booking-code">{invoice.invoice_no}</div>
                    <div className="booking-tour">{invoice.customer_name || '-'}</div>
                  </div>
                  <span className={`status ${getStatusClass(invoice.status)}`}>{invoice.status}</span>
                </div>

                <div className="booking-meta-grid">
                  <div>
                    <span className="booking-meta-label">Booking</span>
                    <span className="booking-meta-value">{invoice.booking_code || '-'}</span>
                  </div>

                  <div>
                    <span className="booking-meta-label">Type</span>
                    <span className="booking-meta-value">{invoice.invoice_type || '-'}</span>
                  </div>

                  <div>
                    <span className="booking-meta-label">Issued</span>
                    <span className="booking-meta-value">{formatDate(invoice.issued_at)}</span>
                  </div>

                  <div>
                    <span className="booking-meta-label">Amount</span>
                    <span className="booking-meta-value booking-meta-value-strong">
                      {formatCurrency(invoice.amount, 'THB')}
                    </span>
                  </div>

                  <div>
                    <span className="booking-meta-label">Email</span>
                    <span className="booking-meta-value">{invoice.customer_email || '-'}</span>
                  </div>

                  <div>
                    <span className="booking-meta-label">Booking Status</span>
                    <span className="booking-meta-value">{invoice.booking_status || '-'}</span>
                  </div>
                </div>

                <div className="booking-row-action">Open invoice →</div>
              </button>
            ))}
          </div>
        )}
      </section>
    </>
  );
}
