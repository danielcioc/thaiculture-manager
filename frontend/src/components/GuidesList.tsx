import type { GuidesResponse } from '../types/guides';
import { SectionHeader, StatCard } from './ui';
import { formatCurrency } from '../utils/formatters';

type GuidesListProps = {
  data: GuidesResponse;
};

export function GuidesList({ data }: GuidesListProps) {
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
        <StatCard label="Total Guides" value={data.count} />

        <StatCard label="Rated Guides" value={ratedCount} />

        <StatCard label="Average Rating" value={averageRating} />

        <StatCard label="Total Default Cost" value={formatCurrency(totalDefaultCost, 'THB')} />
      </div>

      <section className="panel">
        <SectionHeader
          title="Guides"
          subtitle="Field guide profiles and service defaults"
          pill={<span className="meta-pill">{data.count} {data.count === 1 ? 'profile' : 'profiles'}</span>}
        />

        {data.items.length === 0 ? (
          <p>No guides found.</p>
        ) : (
          <div className="guides-list-page">
            {data.items.map((guide) => (
              <article className="guide-row interactive-card" key={guide.id}>
                <div className="guide-row-top">
                  <div>
                    <div className="guide-name">{guide.name}</div>
                    <div className="guide-secondary">
                      {guide.base_area || 'No base area'}
                    </div>
                  </div>
                  <span className="meta-pill guide-pill">
                    {guide.rating !== null ? `Rating ${guide.rating}` : 'No Rating'}
                  </span>
                </div>

                <div className="guide-page-grid">
                  <div>
                    <span className="tour-meta-label">Languages</span>
                    <span className="tour-meta-value">
                      {guide.languages?.length ? guide.languages.join(', ') : '-'}
                    </span>
                  </div>

                  <div>
                    <span className="tour-meta-label">Phone</span>
                    <span className="tour-meta-value">{guide.phone || '-'}</span>
                  </div>

                  <div>
                    <span className="tour-meta-label">LINE ID</span>
                    <span className="tour-meta-value">{guide.line_id || '-'}</span>
                  </div>

                  <div>
                    <span className="tour-meta-label">License No</span>
                    <span className="tour-meta-value">{guide.license_no || '-'}</span>
                  </div>

                  <div>
                    <span className="tour-meta-label">Default Cost</span>
                    <span className="tour-meta-value">
                      {formatCurrency(guide.default_cost, 'THB')}
                    </span>
                  </div>
                </div>

                <div className="tour-notes">
                  <span className="tour-meta-label">Notes</span>
                  <p>{guide.notes || '-'}</p>
                </div>
              </article>
            ))}
          </div>
        )}
      </section>
    </>
  );
}
