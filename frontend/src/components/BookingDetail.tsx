import type { BookingDetailResponse } from '../types/bookings';
import { formatCurrency, formatDate, formatDateTime, formatTime } from '../utils/formatters';
import { getStatusClass } from '../utils/status';

type BookingDetailProps = {
  data: BookingDetailResponse;
  onBack: () => void;
  loading: boolean;
};

function formatTitle(value: string | null | undefined) {
  if (!value) return '-';

  return value
    .split(/[_\s-]+/)
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1).toLowerCase())
    .join(' ');
}

function DetailPair({
  label,
  value,
  strong = false,
}: {
  label: string;
  value: string | number | null | undefined;
  strong?: boolean;
}) {
  return (
    <p>
      <span className="label">{label}</span>
      <span className={strong ? 'value-strong' : undefined}>{value || '-'}</span>
    </p>
  );
}

export function BookingDetail({ data, onBack, loading }: BookingDetailProps) {
  const { booking, payment_summary, operations_summary, payments, assignments } = data;

  return (
    <>
      <div style={{ marginBottom: '20px' }}>
        <button type="button" className="tab" onClick={onBack}>
          ← Back to bookings
        </button>
      </div>

      {loading ? (
        <div className="panel">Loading booking detail...</div>
      ) : (
        <>
          <div className="section-header" style={{ marginBottom: '18px' }}>
            <div>
              <h2 style={{ margin: 0 }}>{booking.booking_code}</h2>
              <p className="section-subtitle">
                {booking.customer_name || '-'} · {booking.tour_name || '-'}
              </p>
            </div>
            <span className={`status ${getStatusClass(booking.status)}`}>{booking.status}</span>
          </div>

          <div className="grid">
            <div className="card">
              <span>Total Revenue</span>
              <strong>
                {formatCurrency(payment_summary.selling_price, payment_summary.currency)}
              </strong>
            </div>

            <div className="card">
              <span>Paid Revenue</span>
              <strong>
                {formatCurrency(payment_summary.paid_amount, payment_summary.currency)}
              </strong>
            </div>

            <div className="card">
              <span>Pending Revenue</span>
              <strong>
                {formatCurrency(payment_summary.pending_amount, payment_summary.currency)}
              </strong>
            </div>

            <div className="card">
              <span>Gross Margin</span>
              <strong>
                {formatCurrency(operations_summary.gross_margin, operations_summary.currency)}
              </strong>
            </div>
          </div>

          <div className="details-grid">
            <div className="stack">
              <section className="panel">
                <h2>Booking Information</h2>

                <div className="detail-list">
                  <div className="detail-row"><span className="label">Booking Code</span><span>{booking.booking_code}</span></div>
                  <div className="detail-row"><span className="label">Customer</span><span>{booking.customer_name || '-'}</span></div>
                  <div className="detail-row"><span className="label">Tour</span><span>{booking.tour_name || '-'}</span></div>
                  <div className="detail-row"><span className="label">Tour Date</span><span>{formatDate(booking.tour_date)}</span></div>
                  <div className="detail-row"><span className="label">Pickup Time</span><span>{formatTime(booking.pickup_time)}</span></div>
                  <div className="detail-row"><span className="label">Guests</span><span>{booking.total_guests || 0}</span></div>
                  <div className="detail-row"><span className="label">Language</span><span>{booking.guide_language || '-'}</span></div>
                  <div className="detail-row"><span className="label">Source</span><span>{booking.source || '-'}</span></div>
                  <div className="detail-row"><span className="label">Pickup Location</span><span>{booking.pickup_location_name || '-'}</span></div>
                  <div className="detail-row"><span className="label">Drop-off</span><span>{booking.dropoff_location_name || '-'}</span></div>
                </div>
              </section>

              <section className="panel">
                <div className="section-header">
                  <div>
                    <h2 style={{ margin: 0 }}>Payments</h2>
                    <p className="section-subtitle">{payments.length} items</p>
                  </div>
                  <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                    <span className={`meta-pill ${getStatusClass(payment_summary.payment_status)}`}>{payment_summary.payment_status}</span>
                    <span className={`meta-pill ${getStatusClass(payment_summary.booking_financial_status)}`}>
                      {formatTitle(payment_summary.booking_financial_status)}
                    </span>
                  </div>
                </div>

                {payments.length === 0 ? (
                  <p>No payment records.</p>
                ) : (
                  <div className="detail-stack">
                    {payments.map((payment) => (
                      <div className="mini-card" key={payment.id}>
                        <div className="mini-card-top">
                          <strong>
                            {formatCurrency(payment.amount, payment.currency)}
                          </strong>
                          <span className={`status ${getStatusClass(payment.status)}`}>{payment.status}</span>
                        </div>

                        <DetailPair label="Method" value={payment.method} />
                        <DetailPair label="Reference" value={payment.reference} />
                        <DetailPair label="Paid At" value={formatDateTime(payment.paid_at)} />
                      </div>
                    ))}
                  </div>
                )}
              </section>
            </div>

            <div className="stack">
              <section className="panel">
                <h2>Operations Summary</h2>

                <div className="detail-list">
                  <div className="detail-row"><span className="label">Guide Cost</span><span>{formatCurrency(operations_summary.guide_cost, operations_summary.currency)}</span></div>
                  <div className="detail-row"><span className="label">Driver Cost</span><span>{formatCurrency(operations_summary.driver_cost, operations_summary.currency)}</span></div>
                  <div className="detail-row"><span className="label">Other Cost</span><span>{formatCurrency(operations_summary.other_cost, operations_summary.currency)}</span></div>
                  <div className="detail-row"><span className="label">Total Cost</span><span>{formatCurrency(operations_summary.total_cost, operations_summary.currency)}</span></div>
                  <div className="detail-row"><span className="label">Gross Margin</span><span>{formatCurrency(operations_summary.gross_margin, operations_summary.currency)}</span></div>
                  <div className="detail-row"><span className="label">Margin %</span><span>{operations_summary.margin_percent}%</span></div>
                </div>
              </section>

              <section className="panel">
                <div className="section-header">
                  <div>
                    <h2 style={{ margin: 0 }}>Assignments</h2>
                    <p className="section-subtitle">{assignments.length} assigned</p>
                  </div>
                </div>

                {assignments.length === 0 ? (
                  <p>No assignments found.</p>
                ) : (
                  <div className="detail-stack">
                    {assignments.map((assignment) => (
                      <div className="mini-card" key={assignment.id}>
                        <div className="mini-card-top">
                          <strong>{formatTitle(assignment.assignment_type)}</strong>
                          <span className={`status ${getStatusClass(assignment.status)}`}>{assignment.status}</span>
                        </div>

                        <DetailPair label="Guide" value={assignment.guide_name} />
                        <DetailPair label="Driver" value={assignment.driver_name} />
                        <DetailPair
                          label="Cost"
                          value={formatCurrency(assignment.cost, operations_summary.currency)}
                          strong
                        />
                        <DetailPair label="Notes" value={assignment.notes} />
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
