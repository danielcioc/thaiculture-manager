import type { CustomersResponse } from '../types/customers';

type CustomersListProps = {
  data: CustomersResponse;
};

export function CustomersList({ data }: CustomersListProps) {
  const withEmail = data.items.filter((item) => Boolean(item.email)).length;
  const withPhone = data.items.filter((item) => Boolean(item.phone || item.whatsapp)).length;
  const languages = Array.from(
    new Set(data.items.map((item) => item.preferred_language).filter(Boolean)),
  );

  return (
    <>
      <div className="grid">
        <div className="card">
          <span>Total Customers</span>
          <strong>{data.count}</strong>
        </div>

        <div className="card">
          <span>With Email</span>
          <strong>{withEmail}</strong>
        </div>

        <div className="card">
          <span>With Phone</span>
          <strong>{withPhone}</strong>
        </div>

        <div className="card">
          <span>Languages</span>
          <strong>{languages.join(', ') || '-'}</strong>
        </div>
      </div>

      <section className="panel">
        <div className="section-header">
          <div>
            <h2 style={{ margin: 0 }}>Customers</h2>
            <p className="section-subtitle">Customer directory overview</p>
          </div>
          <span className="meta-pill">{data.count} total</span>
        </div>

        {data.items.length === 0 ? (
          <p>No customers found.</p>
        ) : (
          <div className="customer-list">
            {data.items.map((customer) => (
              <article className="customer-row" key={customer.id}>
                <div className="customer-row-top">
                  <div>
                    <div className="customer-name">{customer.display_name}</div>
                    <div className="customer-secondary">
                      {customer.country || '-'} · {customer.nationality || '-'}
                    </div>
                  </div>
                  <span className="status">{customer.preferred_language || '-'}</span>
                </div>

                <div className="customer-meta-grid">
                  <div>
                    <span className="customer-meta-label">Email</span>
                    <span className="customer-meta-value">{customer.email || '-'}</span>
                  </div>

                  <div>
                    <span className="customer-meta-label">Phone</span>
                    <span className="customer-meta-value">{customer.phone || '-'}</span>
                  </div>

                  <div>
                    <span className="customer-meta-label">WhatsApp</span>
                    <span className="customer-meta-value">{customer.whatsapp || '-'}</span>
                  </div>
                </div>

                <div className="customer-notes">
                  <span className="customer-meta-label">Notes</span>
                  <p>{customer.notes || 'No customer notes.'}</p>
                </div>
              </article>
            ))}
          </div>
        )}
      </section>
    </>
  );
}
