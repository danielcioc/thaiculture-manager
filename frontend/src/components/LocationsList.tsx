import type { LocationsResponse } from '../types/locations';
import { DetailItem, SectionHeader, StatCard } from './ui';

type LocationsListProps = {
  data: LocationsResponse;
};

export function LocationsList({ data }: LocationsListProps) {
  const cityCount = new Set(data.items.map((item) => item.city || 'Unknown')).size;
  const countryCount = new Set(data.items.map((item) => item.country || 'Unknown')).size;
  const withMapsCount = data.items.filter((item) => Boolean(item.google_maps_url)).length;

  return (
    <>
      <div className="grid">
        <StatCard label="Total Locations" value={data.count} />

        <StatCard label="Cities" value={cityCount} />

        <StatCard label="Countries" value={countryCount} />

        <StatCard label="Mapped Locations" value={withMapsCount} />
      </div>

      <section className="panel">
        <SectionHeader
          title="Locations"
          subtitle="Pickup, drop-off, and reference places"
          pill={<span className="meta-pill">{data.count} {data.count === 1 ? 'location' : 'locations'}</span>}
        />

        {data.items.length === 0 ? (
          <p>No locations found.</p>
        ) : (
          <div className="locations-list-page">
            {data.items.map((location) => (
              <article className="location-row interactive-card" key={location.id}>
                <div className="location-row-top">
                  <div>
                    <div className="location-name">{location.name}</div>
                    <div className="location-secondary">
                      {[location.city, location.country].filter(Boolean).join(', ') || 'Unknown area'}
                    </div>
                  </div>
                  <span className="meta-pill location-pill">
                    {location.google_maps_url ? 'Maps Linked' : 'No Maps Link'}
                  </span>
                </div>

                <div className="location-page-grid">
                  <DetailItem label="Address" value={location.address || '-'} />

                  <DetailItem
                    label="Google Maps"
                    value={location.google_maps_url ? (
                      <a
                        className="tour-link"
                        href={location.google_maps_url}
                        target="_blank"
                        rel="noreferrer"
                      >
                        Open map
                      </a>
                    ) : '-'}
                  />
                </div>
              </article>
            ))}
          </div>
        )}
      </section>
    </>
  );
}
