import { useEffect, useMemo, useState } from 'react';
import { getPricingRules } from '../services/api';
import type { PricingRule, ToursResponse } from '../types/tours';
import { formatDurationHours } from '../utils/formatters';
import { getStatusClass } from '../utils/status';

type ToursListProps = {
  data: ToursResponse;
};

function formatMoney(amount: number | null, currency: string | null) {
  if (amount === null || amount === undefined) return '—';
  return `${currency || 'THB'} ${amount.toLocaleString('en-US', {
    minimumFractionDigits: 0,
    maximumFractionDigits: 2,
  })}`;
}

function formatRuleType(ruleType: string | null | undefined) {
  if (ruleType === 'group_per_person') return 'Per person';
  if (ruleType === 'private_total') return 'Per booking';
  return ruleType || '—';
}

function formatConfidence(confidence: string | null | undefined) {
  if (!confidence) return 'No pricing';
  return confidence.charAt(0).toUpperCase() + confidence.slice(1);
}

function getConfidenceClass(confidence: string | null | undefined) {
  if (confidence === 'confirmed') return getStatusClass('Paid');
  if (confidence === 'estimated') return getStatusClass('Pending');
  return getStatusClass('Draft');
}





export function ToursList({ data }: ToursListProps) {
  const [pricingMap, setPricingMap] = useState<Record<string, PricingRule>>({});
  const [pricingLoading, setPricingLoading] = useState(true);
  const [pricingError, setPricingError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function loadPricing() {
      setPricingLoading(true);
      setPricingError(null);

      try {
        const rules = await getPricingRules();

        if (cancelled) return;

        const nextMap = rules.reduce<Record<string, PricingRule>>((acc, rule) => {
          acc[rule.tour_code] = rule;
          return acc;
        }, {});

        setPricingMap(nextMap);
      } catch (error) {
        if (cancelled) return;
        setPricingError(error instanceof Error ? error.message : 'Failed to load pricing.');
      } finally {
        if (!cancelled) {
          setPricingLoading(false);
        }
      }
    }

    loadPricing();

    return () => {
      cancelled = true;
    };
  }, []);

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

  const pricedCount = useMemo(
    () => data.items.filter((item) => pricingMap[item.tour_code]).length,
    [data.items, pricingMap],
  );

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

        <div className="card">
          <span>With Pricing</span>
          <strong>{pricingLoading ? '...' : pricedCount}</strong>
        </div>
      </div>

      <section className="panel">
        <div className="section-header">
          <div>
            <h2 style={{ margin: 0 }}>Tours</h2>
            <p className="section-subtitle">Tour catalog overview with pricing</p>
          </div>
          <span className="meta-pill">{data.count} total</span>
        </div>

        {pricingError ? (
          <p style={{ color: '#b42318' }}>Pricing unavailable: {pricingError}</p>
        ) : null}

        {data.items.length === 0 ? (
          <p>No tours found.</p>
        ) : (
          <div className="tour-list">
            {data.items.map((tour) => {
              const pricing = pricingMap[tour.tour_code];

              return (
                <article className="tour-row interactive-card" key={tour.id}>
                  <div className="tour-row-top">
                    <div>
                      <div className="tour-name">{tour.name}</div>
                      <div className="tour-secondary">
                        {tour.tour_code} · {tour.category || 'Uncategorized'}
                      </div>
                    </div>
                    <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap', justifyContent: 'flex-end' }}>
                      <span className={`status ${getStatusClass(tour.is_active ? 'Active' : 'Inactive')}`}>
                        {tour.is_active ? 'Active' : 'Inactive'}
                      </span>
                      <span className={`status ${getConfidenceClass(pricing?.confidence_status)}`}>
                        {formatConfidence(pricing?.confidence_status)}
                      </span>
                    </div>
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

                    <div>
                      <span className="tour-meta-label">Selling price</span>
                      <span className="tour-meta-value">
                        {pricing
                          ? formatMoney(pricing.selling_price_gross, pricing.currency)
                          : '—'}
                      </span>
                    </div>

                    <div>
                      <span className="tour-meta-label">Pricing model</span>
                      <span className="tour-meta-value">
                        {pricing ? formatRuleType(pricing.rule_type) : '—'}
                      </span>
                    </div>

                    <div>
                      <span className="tour-meta-label">Direct cost</span>
                      <span className="tour-meta-value">
                        {pricing
                          ? formatMoney(pricing.direct_cost_total, pricing.currency)
                          : '—'}
                      </span>
                    </div>
                  </div>

                  {pricing ? (
                    <div className="tour-notes">
                      <span className="tour-meta-label">Pricing notes</span>
                      <p style={{ marginBottom: '0.35rem' }}>
                        {pricing.rule_type === 'group_per_person'
                          ? `Displayed as ${formatMoney(pricing.selling_price_gross, pricing.currency)} per person.`
                          : `Displayed as ${formatMoney(pricing.selling_price_gross, pricing.currency)} per booking.`}
                      </p>
                      <p style={{ marginBottom: '0.35rem' }}>
                        Includes: {pricing.includes || '—'}
                      </p>
                      <p style={{ marginBottom: '0.35rem' }}>
                        Excludes: {pricing.excludes || '—'}
                      </p>
                      <p style={{ marginBottom: 0 }}>
                        Insurance rule: {pricing.insurance_rule || '—'}
                      </p>
                    </div>
                  ) : (
                    <div className="tour-notes">
                      <span className="tour-meta-label">Pricing notes</span>
                      <p style={{ marginBottom: 0 }}>No pricing rule saved for this tour yet.</p>
                    </div>
                  )}

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
              );
            })}
          </div>
        )}
      </section>
    </>
  );
}
