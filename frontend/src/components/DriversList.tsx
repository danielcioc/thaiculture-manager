import type { DriversResponse } from '../types/drivers';
import { SectionHeader, StatCard } from './ui';
import { formatCurrency } from '../utils/formatters';

type DriversListProps = {
  data: DriversResponse;
};

export function DriversList({ data }: DriversListProps) {
  const ratedCount = data.items.filter((item) => item.rating !== null).length;
  const averageRating = ratedCount
    ? (
        data.items.reduce((sum, item) => sum + Number(item.rating || 0), 0) / ratedCount
      ).toFixed(1)
    : '-';
  const totalDefaultCost = data.items.reduce(
    (sum, item) => sum + Number(item.default_cost || 0),
    0,
  );

  return (
    <>
      <div className="grid">
        <StatCard label="Total Drivers" value={data.count} />

        <StatCard label="Rated Drivers" value={ratedCount} />

        <div className="card">
          <span>Average Rating</span>
          <strong>{averageRating}</strong>
        </div>

        <StatCard label="Total Default Cost" value={formatCurrency(totalDefaultCost, 'THB')} />
      </div>

      <section className="panel">
        <SectionHeader
          title="Drivers"
          subtitle="Vehicle and transport partners"
          pill={<span className="meta-pill">{data.count} {data.count === 1 ? 'profile' : 'profiles'}</span>}
        />

        {data.items.length === 0 ? (
          <p>No drivers found.</p>
        ) : (
          <div className="drivers-list-page">
            {data.items.map((driver) => (
              <article className="driver-row interactive-card" key={driver.id}>
                <div className="driver-row-top">
                  <div>
                    <div className="driver-name">{driver.name}</div>
                    <div className="driver-secondary">
                      {driver.base_area || 'No base area'}
                    </div>
                  </div>
                  <span className="meta-pill driver-pill">
                    {driver.rating !== null ? `Rating ${driver.rating}` : 'No Rating'}
                  </span>
                </div>

                <div className="driver-page-grid">
                  <div>
                    <span className="tour-meta-label">Phone</span>
                    <span className="tour-meta-value">{driver.phone || '-'}</span>
                  </div>

                  <div>
                    <span className="tour-meta-label">LINE ID</span>
                    <span className="tour-meta-value">{driver.line_id || '-'}</span>
                  </div>

                  <div>
                    <span className="tour-meta-label">Base Area</span>
                    <span className="tour-meta-value">{driver.base_area || '-'}</span>
                  </div>

                  <div>
                    <span className="tour-meta-label">Default Cost</span>
                    <span className="tour-meta-value">
                      {formatCurrency(driver.default_cost, 'THB')}
                    </span>
                  </div>
                </div>
              </article>
            ))}
          </div>
        )}
      </section>
    </>
  );
}
