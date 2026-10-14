import type { BookingDetailResponse } from '../types/bookings';
import { formatCurrency, formatDate, formatDateTime, formatTime } from '../utils/formatters';
import { getStatusClass } from '../utils/status';

const bookingFinancialStatusLabel: Record<string, string> = {
  unpaid: 'Unpaid',
  depositrequested: 'Deposit Requested',
  depositpaid: 'Deposit Paid',
  partiallypaid: 'Partially Paid',
  paid: 'Paid',
};

type BookingDetailProps = {
  data: BookingDetailResponse;
  onBack: () => void;
  loading: boolean;
};

function formatTitle(value: string | null | undefined) {
  if (!value) return '-';

  const normalized = value.toLowerCase().replace(/[_\\s-]+/g, '');
  if (bookingFinancialStatusLabel[normalized]) return bookingFinancialStatusLabel[normalized];

  return value
    .split(/[_\\s-]+/)
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1).toLowerCase())
    .join(' ');
}

function formatPricingBasis(pricingUse: string | null | undefined) {
  if (!pricingUse) return '-';

  const normalized = pricingUse.toLowerCase().replace(/[_\\s-]+/g, '');
  if (normalized.includes('person')) return 'Displayed per person';
  if (normalized.includes('booking') || normalized.includes('group') || normalized.includes('private')) {
    return 'Displayed per booking';
  }

  return formatTitle(pricingUse);
}

function formatBooleanLabel(value: boolean | null | undefined) {
  if (value === null || value === undefined) return '-';
  return value ? 'Yes' : 'No';
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
                  <div className="detail-row">
                    <span className="label">Imported Tour Name</span>
                    <span>{booking.imported_raw_tour_name || '-'}</span>
                  </div>
                  <div className="detail-row">
                    <span className="label">Mapping Status</span>
                    <span>{booking.mapping_status || '-'}</span>
                  </div>
                  <div className="detail-row">
                    <span className="label">Manual Review</span>
                    <span>
                      {booking.needs_manual_review ? (
                        <span className="status needs-review">Needs review</span>
                      ) : (
                        'No'
                      )}
                    </span>
                  </div>
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
                <div className="section-header">
                  <div>
                    <h2 style={{ margin: 0 }}>Operations Summary</h2>
                    <p className="section-subtitle">Pricing and operational cost detail</p>
                  </div>
                  <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                    {operations_summary.cost_status && (
                      <span className={`meta-pill ${getStatusClass(operations_summary.cost_status)}`}>
                        Cost: {formatTitle(operations_summary.cost_status)}
                      </span>
                    )}
                    {operations_summary.pricing_use && (
                      <span className={`meta-pill ${getStatusClass(operations_summary.pricing_use)}`}>
                        Use: {formatTitle(operations_summary.pricing_use)}
                      </span>
                    )}
                    {operations_summary.direct_cost_is_known !== null && operations_summary.direct_cost_is_known !== undefined && (
                      <span className={`meta-pill ${getStatusClass(operations_summary.direct_cost_is_known ? 'Paid' : 'Pending')}`}>
                        Direct cost known: {formatBooleanLabel(operations_summary.direct_cost_is_known)}
                      </span>
                    )}
                  </div>
                </div>

                <div className="detail-list">
                  <div className="detail-row"><span className="label">Revenue</span><span>{formatCurrency(payment_summary.selling_price, payment_summary.currency)}</span></div>
                  <div className="detail-row"><span className="label">Revenue Basis</span><span>{formatPricingBasis(operations_summary.pricing_use)}</span></div>
                  <div className="detail-row"><span className="label">Pricing Use</span><span>{formatTitle(operations_summary.pricing_use)}</span></div>
                  <div className="detail-row"><span className="label">Cost Status</span><span>{formatTitle(operations_summary.cost_status)}</span></div>
                  <div className="detail-row"><span className="label">Direct Cost Known</span><span>{formatBooleanLabel(operations_summary.direct_cost_is_known)}</span></div>
                  <div className="detail-row"><span className="label">Guide Cost</span><span>{formatCurrency(operations_summary.guide_cost, operations_summary.currency)}</span></div>
                  <div className="detail-row"><span className="label">Driver Cost</span><span>{formatCurrency(operations_summary.driver_cost, operations_summary.currency)}</span></div>
                  <div className="detail-row"><span className="label">Other Cost</span><span>{formatCurrency(operations_summary.other_cost, operations_summary.currency)}</span></div>
                  <div className="detail-row"><span className="label">Total Cost</span><span>{formatCurrency(operations_summary.total_cost, operations_summary.currency)}</span></div>
                  <div className="detail-row"><span className="label">Gross Margin</span><span>{formatCurrency(operations_summary.gross_margin, operations_summary.currency)}</span></div>
                  <div className="detail-row"><span className="label">Margin %</span><span>{operations_summary.margin_percent ?? '-'}{operations_summary.margin_percent !== null && operations_summary.margin_percent !== undefined ? '%' : ''}</span></div>
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
