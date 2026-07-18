import type { InvoiceDetailResponse } from '../types/invoices';
import { formatCurrency, formatDate } from '../utils/formatters';
import { getStatusClass } from '../utils/status';

type InvoiceDetailProps = {
  data: InvoiceDetailResponse;
  onBack: () => void;
  loading: boolean;
};

export function InvoiceDetail({ data, onBack, loading }: InvoiceDetailProps) {
  const { invoice, items } = data;

  return (
    <>
      <div style={{ marginBottom: '20px' }}>
        <button type="button" className="tab" onClick={onBack}>
          ← Back to invoices
        </button>
      </div>

      {loading ? (
        <div className="panel">Loading invoice detail...</div>
      ) : (
        <>
          <div className="section-header" style={{ marginBottom: '18px' }}>
            <div>
              <h2 style={{ margin: 0 }}>{invoice.invoice_no}</h2>
              <p className="section-subtitle">
                {invoice.customer_name || '-'} · {invoice.booking_code || '-'}
              </p>
            </div>
            <span className={`status ${getStatusClass(invoice.status)}`}>{invoice.status}</span>
          </div>

          <div className="grid">
            <div className="card">
              <span>Total Amount</span>
              <strong>{formatCurrency(invoice.amount, 'THB')}</strong>
            </div>

            <div className="card">
              <span>Items</span>
              <strong>{items.length}</strong>
            </div>

            <div className="card">
              <span>Invoice Type</span>
              <strong>{invoice.invoice_type || '-'}</strong>
            </div>

            <div className="card">
              <span>Issued At</span>
              <strong>{formatDate(invoice.issued_at)}</strong>
            </div>
          </div>

          <div className="details-grid">
            <div className="stack">
              <section className="panel">
                <h2>Invoice Information</h2>

                <div className="detail-list">
                  <div className="detail-row"><span className="label">Invoice No</span><span>{invoice.invoice_no}</span></div>
                  <div className="detail-row"><span className="label">Customer</span><span>{invoice.customer_name || '-'}</span></div>
                  <div className="detail-row"><span className="label">Email</span><span>{invoice.customer_email || '-'}</span></div>
                  <div className="detail-row"><span className="label">Booking Code</span><span>{invoice.booking_code || '-'}</span></div>
                  <div className="detail-row"><span className="label">Booking Status</span><span>{invoice.booking_status || '-'}</span></div>
                  <div className="detail-row"><span className="label">Booking Source</span><span>{invoice.booking_source || '-'}</span></div>
                  <div className="detail-row"><span className="label">Issued At</span><span>{formatDate(invoice.issued_at)}</span></div>
                </div>
              </section>
            </div>

            <div className="stack">
              <section className="panel">
                <div className="section-header">
                  <div>
                    <h2 style={{ margin: 0 }}>Invoice Items</h2>
                    <p className="section-subtitle">{items.length} items</p>
                  </div>
                </div>

                {items.length === 0 ? (
                  <p>No invoice items found.</p>
                ) : (
                  <div className="detail-stack">
                    {items.map((item) => (
                      <div className="mini-card" key={item.id}>
                        <div className="mini-card-top">
                          <strong>{item.description}</strong>
                          <span className="status">{formatCurrency(item.line_amount, 'THB')}</span>
                        </div>
                        <p><span className="label">Service Date</span><span>{formatDate(item.service_date)}</span></p>
                        <p><span className="label">Booking Code</span><span>{item.booking_code || '-'}</span></p>
                        <p><span className="label">Quantity</span><span>{item.qty}</span></p>
                        <p><span className="label">Unit Amount</span><span>{formatCurrency(item.unit_amount, 'THB')}</span></p>
                      </div>
                    ))}
                  </div>
                )}
              </section>
            </div>
          </div>
        </>
      )}
    </>
  );
}
