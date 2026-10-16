(() => {
  const root = document.getElementById('tct-local-booking-widget');
  if (!root) return;

  root.innerHTML = `
    <section class="tct-local-card">
      <p class="tct-local-kicker">ThaiCulture Manager · local demo</p>
      <h2>Request a quote</h2>
      <p class="tct-local-intro">The Manager calculates the quote. Submitting this form creates an inquiry, not a confirmed tour.</p>
      <form id="tct-local-form">
        <label>Travel date<input name="date" type="date" required></label>
        <div class="tct-local-grid">
          <label>Adults<input name="adults" type="number" min="0" max="30" value="2" required></label>
          <label>Children<input name="children" type="number" min="0" max="30" value="2" required></label>
        </div>
        <label>Full name<input name="name" autocomplete="name" maxlength="255" required></label>
        <label>Email<input name="email" type="email" autocomplete="email" required></label>
        <label>Phone<input name="phone" type="tel" autocomplete="tel" maxlength="50" required></label>
        <label>Notes<textarea name="notes" rows="3" maxlength="2000"></textarea></label>
        <button type="button" id="tct-local-price">Calculate from Manager</button>
        <div id="tct-local-price-result" aria-live="polite"></div>
        <button type="submit" id="tct-local-submit" disabled>Send inquiry</button>
        <p id="tct-local-message" role="status" aria-live="polite"></p>
      </form>
    </section>`;
  const style = document.createElement('style');
  style.textContent = `
    #tct-local-integration{max-width:72rem;margin:2rem auto;padding:0 1rem}
    .tct-local-card{max-width:34rem;margin:auto;padding:1.5rem;border:1px solid #f1d7a6;border-radius:1rem;background:#fff;box-shadow:0 8px 30px #1f29371a;color:#1f2937}
    .tct-local-card h2{font-size:1.5rem;font-weight:700;margin:.25rem 0}.tct-local-kicker{font-size:.7rem;letter-spacing:.12em;text-transform:uppercase;color:#b7791f}.tct-local-intro{font-size:.9rem;color:#536171;margin:.5rem 0 1rem}
    .tct-local-card form,.tct-local-card label{display:grid;gap:.4rem}.tct-local-card form{gap:.8rem}.tct-local-card label{font-size:.85rem;font-weight:600}.tct-local-card input,.tct-local-card textarea{width:100%;border:1px solid #cbd5e1;border-radius:.5rem;padding:.65rem;font:inherit}.tct-local-grid{display:grid;grid-template-columns:1fr 1fr;gap:.8rem}
    .tct-local-card button{border:0;border-radius:999px;background:#d99017;color:#fff;font-weight:700;padding:.8rem;cursor:pointer}.tct-local-card button:disabled{opacity:.45;cursor:not-allowed}#tct-local-price-result{font-size:1.05rem;font-weight:700}#tct-local-message{font-size:.9rem;min-height:1.3em;color:#374151}
    @media(max-width:520px){.tct-local-card{padding:1rem}.tct-local-grid{grid-template-columns:1fr 1fr}}
  `;
  document.head.append(style);

  const form = root.querySelector('#tct-local-form');
  const priceButton = root.querySelector('#tct-local-price');
  const submitButton = root.querySelector('#tct-local-submit');
  const result = root.querySelector('#tct-local-price-result');
  const message = root.querySelector('#tct-local-message');
  const tourId = location.pathname.split('/').pop();
  let currentQuote = null;
  let catalogTour = null;
  let idempotencyKey = null;
  let idempotencyPayload = null;

  const requestData = () => {
    const fields = new FormData(form);
    return {
      website_tour_id: tourId,
      date: fields.get('date'),
      adults: Number(fields.get('adults')),
      children: Number(fields.get('children')),
      extras: [],
      currency: 'THB',
    };
  };
  const reportError = async (response) => {
    let body = {};
    try { body = await response.json(); } catch {}
    const conflict = response.status === 409 ? 'The quote or request changed. Recalculate and submit again.' : '';
    const detail = Array.isArray(body.detail)
      ? body.detail.map((item) => item.msg || 'Invalid input').join('; ')
      : typeof body.detail === 'string' ? body.detail : '';
    throw new Error(conflict || detail || `Manager request failed (${response.status})`);
  };

  fetch('/api/website/catalog')
    .then(async (response) => {
      if (!response.ok) await reportError(response);
      const catalog = await response.json();
      catalogTour = catalog.items.find((item) => item.website_tour_id === tourId) || null;
      if (!catalogTour) throw new Error('This tour has no active Manager pricing rule.');
      root.querySelector('.tct-local-intro').textContent = `Manager pricing available for ${catalogTour.english_title}. The request creates an inquiry, not a confirmed tour.`;
    })
    .catch((error) => {
      message.textContent = error.message || 'Could not load the Manager tour catalog.';
      priceButton.disabled = true;
    });

  priceButton.addEventListener('click', async () => {
    if (!catalogTour) {
      message.textContent = 'This tour is not currently configured for Manager pricing.';
      return;
    }
    message.textContent = 'Calculating…';
    result.textContent = '';
    submitButton.disabled = true;
    currentQuote = null;
    try {
      const response = await fetch('/api/website/pricing', {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(requestData()),
      });
      if (!response.ok) await reportError(response);
      currentQuote = await response.json();
      result.textContent = `Total from Manager: ${currentQuote.total.toLocaleString()} ${currentQuote.currency}`;
      message.textContent = `Quote valid until ${new Date(currentQuote.expires_at).toLocaleString()}.`;
      submitButton.disabled = false;
    } catch (error) {
      message.textContent = error.message || 'Could not calculate the quote.';
    }
  });

  form.addEventListener('input', () => {
    const changed = JSON.stringify(requestData());
    if (currentQuote && changed !== JSON.stringify({ ...requestData(), website_tour_id: currentQuote.website_tour_id })) {
      currentQuote = null;
      submitButton.disabled = true;
      result.textContent = '';
      message.textContent = 'Inputs changed. Calculate a fresh quote.';
    }
    idempotencyKey = null;
    idempotencyPayload = null;
  });

  form.addEventListener('submit', async (event) => {
    event.preventDefault();
    if (!currentQuote) return;
    const fields = new FormData(form);
    const payload = {
      quote_id: currentQuote.quote_id,
      date: fields.get('date'), adults: Number(fields.get('adults')),
      children: Number(fields.get('children')), extras: [], currency: currentQuote.currency,
      customer: { name: fields.get('name'), email: fields.get('email'), phone: fields.get('phone') },
      notes: fields.get('notes') || '',
    };
    const encoded = JSON.stringify(payload);
    if (!idempotencyKey || idempotencyPayload !== encoded) {
      idempotencyKey = crypto.randomUUID();
      idempotencyPayload = encoded;
    }
    submitButton.disabled = true;
    message.textContent = 'Sending inquiry…';
    try {
      const response = await fetch('/api/website/bookings', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Idempotency-Key': idempotencyKey },
        body: encoded,
      });
      if (!response.ok) await reportError(response);
      const booking = await response.json();
      message.textContent = `Inquiry received: ${booking.booking_reference} · ${booking.total.toLocaleString()} ${booking.currency}. No proforma has been created.`;
      currentQuote = null;
      result.textContent = '';
    } catch (error) {
      message.textContent = `${error.message || 'The inquiry could not be sent.'} Retry with the same inputs to avoid duplicates.`;
      submitButton.disabled = false;
    }
  });
})();
