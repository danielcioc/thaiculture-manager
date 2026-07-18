import type { ToursResponse } from '../types/tours';
import { formatDurationHours } from '../utils/formatters';
import { getStatusClass } from '../utils/status';

type ToursListProps = {
  data: ToursResponse;
};

export function ToursList({ data }: ToursListProps) {
  const activeCount = data.items.filter((item) => item.is_active).length;
  const categories = Array.from(
    new Set(data.items.map((item) => item.category).filter(Boolean)),
  );
  const avgDuration = data.items.length
    ? (
        data.items.reduce(
          (sum, item) => sum + Number(item.default_duration_hours || 0),
          0,
        ) / data.items.length
      ).toFixed(1)
    : '0.0';

  return (
    <>
      <div className="grid">
        <div className="card">
          <span>Total Tours</span>
          <strong>{data.count}</strong>
        </div>

        <div className="card">
          <span>Active Tours</span>
          <strong>{activeCount}</strong>
        </div>

        <div className="card">
          <span>Categories</span>
          <strong>{categories.length}</strong>
        </div>

        <div className="card">
          <span>Avg Duration</span>
          <strong>{formatDurationHours(avgDuration)}</strong>
        </div>
      </div>

      <section className="panel">
        <div className="section-header">
          <div>
            <h2 style={{ margin: 0 }}>Tours</h2>
            <p className="section-subtitle">Tour catalog overview</p>
          </div>
          <span className="meta-pill">{data.count} total</span>
        </div>

        {data.items.length === 0 ? (
          <p>No tours found.</p>
        ) : (
          <div className="tour-list">
            {data.items.map((tour) => (
              <article className="tour-row interactive-card" key={tour.id}>
                <div className="tour-row-top">
                  <div>
                    <div className="tour-name">{tour.name}</div>
                    <div className="tour-secondary">
                      {tour.tour_code} · {tour.category || 'Uncategorized'}
                    </div>
                  </div>
                  <span className={`status ${getStatusClass(tour.is_active ? 'Active' : 'Inactive')}`}>{tour.is_active ? 'Active' : 'Inactive'}</span>
                </div>

                <div className="tour-meta-grid">
                  <div>
                    <span className="tour-meta-label">Code</span>
                    <span className="tour-meta-value">{tour.tour_code}</span>
                  </div>

                  <div>
                    <span className="tour-meta-label">Category</span>
                    <span className="tour-meta-value">{tour.category || '-'}</span>
                  </div>

                  <div>
                    <span className="tour-meta-label">Duration</span>
                    <span className="tour-meta-value">
                      {formatDurationHours(tour.default_duration_hours)}
                    </span>
                  </div>
                </div>

                <div className="tour-notes">
                  <span className="tour-meta-label">Website</span>
                  {tour.website_url ? (
                    <a href={tour.website_url} target="_blank" rel="noreferrer">
                      {tour.website_url}
                    </a>
                  ) : (
                    <p>No website link.</p>
                  )}
                </div>
              </article>
            ))}
          </div>
        )}
      </section>
    </>
  );
}
