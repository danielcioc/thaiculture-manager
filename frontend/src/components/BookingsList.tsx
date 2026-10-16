import type { BookingsResponse } from '../types/bookings';
import type { PricingQuote } from '../types/tours';
import { formatCurrency, formatDate, formatTime } from '../utils/formatters';
import { getStatusClass } from '../utils/status';

type ReviewFilter = 'all' | 'needs_review' | 'no_review';

function formatQuoteLabel(value: string | boolean | null | undefined) {
  if (value === null || value === undefined) return '—';
  if (typeof value === 'boolean') return value ? 'Yes' : 'No';
  return value
    .replace(/_/g, ' ')
    .replace(/\b\w/g, (char) => char.toUpperCase());
}

function formatMappingStatus(value: string) {
  return value.replace(/_/g, ' ').replace(/\b\w/g, (char) => char.toUpperCase());
}

type BookingsListProps = {
  data: BookingsResponse;
  pricingQuotes: PricingQuote[];
  reviewFilter: ReviewFilter;
  onReviewFilterChange: (filter: ReviewFilter) => void;
  onSelectBooking: (bookingCode: string) => void;
};

export function BookingsList({
  data,
  pricingQuotes,
  reviewFilter,
  onReviewFilterChange,
  onSelectBooking,
}: BookingsListProps) {
  const totalRevenue = data.items.reduce(
    (sum, item) => sum + Number(item.selling_price || 0),
    0,
  );
  const totalGuests = data.items.reduce(
    (sum, item) => sum + Number(item.total_guests || 0),
    0,
  );
  const confirmedCount = data.items.filter(
    (item) => item.status === 'Confirmed',
  ).length;
  const currency = data.items[0]?.currency ?? 'THB';

  const pricingQuotesMap = pricingQuotes.reduce<Record<string, PricingQuote>>((acc, quote) => {
    acc[quote.booking_id] = quote;
    return acc;
  }, {});

  return (
    <>
      <div className="grid">
        <div className="card">
          <span>Total Bookings</span>
          <strong>{data.items.length}</strong>
        </div>

        <div className="card">
          <span>Confirmed</span>
          <strong>{confirmedCount}</strong>
        </div>

        <div className="card">
          <span>Total Guests</span>
          <strong>{totalGuests}</strong>
        </div>

        <div className="card">
          <span>Total Revenue</span>
          <strong>{formatCurrency(totalRevenue, currency)}</strong>
        </div>
      </div>

      <section className="panel">
        <div className="section-header">
          <div>
            <h2 style={{ margin: 0 }}>Bookings</h2>
            <p className="section-subtitle">Operational booking overview</p>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px', flexWrap: 'wrap' }}>
            <label htmlFor="booking-review-filter" className="booking-meta-label">
              Review status
            </label>
            <select
              id="booking-review-filter"
              value={reviewFilter}
              onChange={(event) => onReviewFilterChange(event.target.value as ReviewFilter)}
              onClick={(event) => event.stopPropagation()}
              style={{
                background: 'var(--surface, #111827)',
                color: 'inherit',
                border: '1px solid var(--border, #334155)',
                borderRadius: '8px',
                padding: '8px 10px',
              }}
            >
              <option value="all">All</option>
              <option value="needs_review">Needs review</option>
              <option value="no_review">No review needed</option>
            </select>
            <span className="meta-pill">{data.count} total</span>
          </div>
        </div>

        {data.items.length === 0 ? (
          <p>No bookings found.</p>
        ) : (
          <div className="booking-list">
            {data.items.map((booking) => {
              const pricingQuote = pricingQuotesMap[booking.id];

              return (
                <button
                  type="button"
                  className="booking-row interactive-card"
                  key={booking.id}
                  onClick={() => onSelectBooking(booking.booking_code)}
                >
                  <div className="booking-row-top">
                    <div>
                      <div className="booking-code">{booking.booking_code}</div>
                      <div className={`booking-tour${booking.tour_name ? '' : ' missing-canonical-tour'}`}>
                        {booking.tour_name || 'Needs review'}
                      </div>
                      {booking.booking_financial_status && (
                        <div className="booking-financial-inline">
                          <span className={`meta-pill ${getStatusClass(booking.booking_financial_status)}`}>
                            {booking.booking_financial_status}
                          </span>
                          <span>Paid {formatCurrency(booking.paid_amount, booking.currency)}</span>
                          <span>Balance {formatCurrency(booking.balance_due, booking.currency)}</span>
                        </div>
                      )}
                    </div>
                    <span className={`status ${getStatusClass(booking.status)}`}>
                      {booking.status}
                    </span>
                  </div>

                  {(booking.imported_raw_tour_name || booking.mapping_status || booking.needs_manual_review) && (
                    <div className="import-review-metadata">
                      {booking.imported_raw_tour_name && (
                        <span className="imported-tour-label">
                          Imported label: {booking.imported_raw_tour_name}
                        </span>
                      )}
                      <div className="import-review-badges">
                        {booking.mapping_status && (
                          <span className={`status mapping-badge mapping-${booking.mapping_status}`}>
                            Mapping: {formatMappingStatus(booking.mapping_status)}
                          </span>
                        )}
                        {booking.needs_manual_review && (
                          <span className="status needs-review">Needs review</span>
                        )}
                      </div>
                    </div>
                  )}

                  {pricingQuote && (
                    <div style={{ marginTop: '8px', display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                      <span className={`status ${getStatusClass(pricingQuote.compatibility_status || 'Draft')}`}>
                        Compatibility: {formatQuoteLabel(pricingQuote.compatibility_status)}
                      </span>
                      <span className={`status ${getStatusClass(pricingQuote.cost_status || 'Pending')}`}>
                        Cost: {formatQuoteLabel(pricingQuote.cost_status)}
                      </span>
                      <span className={`status ${getStatusClass(pricingQuote.pricing_use || 'Draft')}`}>
                        Use: {formatQuoteLabel(pricingQuote.pricing_use)}
                      </span>
                      <span className={`status ${getStatusClass(pricingQuote.direct_cost_is_known ? 'Paid' : 'Pending')}`}>
                        Direct cost known: {formatQuoteLabel(pricingQuote.direct_cost_is_known)}
                      </span>
                      {pricingQuote.margin_verdict && (
                        <span className={`status ${getStatusClass(pricingQuote.margin_verdict)}`}>
                          Margin: {formatQuoteLabel(pricingQuote.margin_verdict)}
                        </span>
                      )}
                      {pricingQuote.approval_status === 'manual_override_required' && (
                        <span className="status needs-review">Manual approval required</span>
                      )}
                    </div>
                  )}

                  <div className="booking-meta-grid">
                    <div>
                      <span className="booking-meta-label">Customer</span>
                      <span className="booking-meta-value">{booking.customer_name || '-'}</span>
                    </div>

                    <div>
                      <span className="booking-meta-label">Date</span>
                      <span className="booking-meta-value">{formatDate(booking.tour_date)}</span>
                    </div>

                    <div>
                      <span className="booking-meta-label">Pickup Time</span>
                      <span className="booking-meta-value">{formatTime(booking.pickup_time)}</span>
                    </div>

                    <div>
                      <span className="booking-meta-label">Guests</span>
                      <span className="booking-meta-value">{booking.total_guests}</span>
                    </div>

                    <div>
                      <span className="booking-meta-label">Language</span>
                      <span className="booking-meta-value">{booking.guide_language || '-'}</span>
                    </div>

                    <div>
                      <span className="booking-meta-label">Pickup</span>
                      <span className="booking-meta-value">{booking.pickup_location_name || '-'}</span>
                    </div>

                    <div>
                      <span className="booking-meta-label">Source</span>
                      <span className="booking-meta-value">{booking.source || '-'}</span>
                    </div>

                    <div>
                      <span className="booking-meta-label">Revenue</span>
                      <span className="booking-meta-value booking-meta-value-strong">
                        {formatCurrency(booking.selling_price, booking.currency)}
                      </span>
                    </div>
                  </div>

                  <div className="booking-row-action">Open booking →</div>
                </button>
              );
            })}
          </div>
        )}
      </section>
    </>
  );
}
