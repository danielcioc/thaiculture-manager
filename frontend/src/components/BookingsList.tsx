import type { BookingsResponse } from '../types/bookings';
import { formatCurrency, formatDate, formatTime } from '../utils/formatters';
import { getStatusClass } from '../utils/status';

type ReviewFilter = 'all' | 'needs_review' | 'no_review';

type BookingsListProps = {
  data: BookingsResponse;
  reviewFilter: ReviewFilter;
  onReviewFilterChange: (filter: ReviewFilter) => void;
  onSelectBooking: (bookingCode: string) => void;
};

export function BookingsList({
  data,
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
          <strong>
            {formatCurrency(totalRevenue, currency)}
          </strong>
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
            {data.items.map((booking) => (
              <button
                type="button"
                className="booking-row interactive-card"
                key={booking.id}
                onClick={() => onSelectBooking(booking.booking_code)}
              >
                <div className="booking-row-top">
                  <div>
                    <div className="booking-code">{booking.booking_code}</div>
                    <div className="booking-tour">{booking.tour_name || '-'}</div>
                  </div>
                  <span className={`status ${getStatusClass(booking.status)}`}>{booking.status}</span>
                </div>

                {booking.needs_manual_review && (
                  <div style={{ marginTop: '8px' }}>
                    <span className="status needs-review">Needs review</span>
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
            ))}
          </div>
        )}
      </section>
    </>
  );
}
