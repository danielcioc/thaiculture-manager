import assert from 'node:assert/strict';
import test from 'node:test';
import React from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { createServer } from 'vite';
import react from '@vitejs/plugin-react';

const vite = await createServer({
  configFile: false,
  plugins: [react()],
  server: { middlewareMode: true, hmr: false },
  appType: 'custom',
  optimizeDeps: { noDiscovery: true, include: [] },
});

const { PaymentsList } = await vite.ssrLoadModule('/src/components/PaymentsList.tsx');
const { BookingDetail } = await vite.ssrLoadModule('/src/components/BookingDetail.tsx');

test.after(async () => vite.close());

const paymentProps = (overrides = {}) => ({
  data: { count: 0, items: [] },
  summary: { currencies: [] },
  loading: false,
  error: '',
  statusFilter: 'all',
  sortBy: 'paid_at',
  sortOrder: 'desc',
  onStatusFilterChange() {},
  onSortChange() {},
  ...overrides,
});

test('Payments view has loading, empty and API error states', () => {
  const loading = renderToStaticMarkup(React.createElement(PaymentsList, paymentProps({ loading: true })));
  const empty = renderToStaticMarkup(React.createElement(PaymentsList, paymentProps()));
  const error = renderToStaticMarkup(React.createElement(PaymentsList, paymentProps({ data: null, error: 'API unavailable' })));
  assert.match(loading, /Loading payments/);
  assert.match(empty, /No payments found/);
  assert.match(error, /Unable to load payments/);
});

test('Payments view renders statuses and explicit multi-currency mismatch feedback', () => {
  const html = renderToStaticMarkup(React.createElement(PaymentsList, paymentProps({
    data: { count: 5, items: ['paid', 'pending', 'overdue', 'cancelled', 'draft'].map((status, index) => ({
      id: String(index), amount: 100, currency: index === 4 ? 'USD' : 'THB', booking_currency: 'THB',
      currency_matches_booking: index !== 4, financial_error: index === 4 ? 'currency_mismatch' : null,
      method: 'Cash', status, booking_code: 'TCT-TEST', customer_name: 'Test',
      paid_at: null, due_at: null, reference: null, notes: null,
    })) },
    summary: { currencies: [{ currency: 'THB', collected_amount: 100, currency_mismatch_count: 1,
      draft_count: 1, requested_count: 0, pending_count: 1, paid_count: 1,
      partiallypaid_count: 0, overdue_count: 1, cancelled_count: 1 }] },
  })));
  for (const status of ['paid', 'pending', 'overdue', 'cancelled', 'draft']) assert.match(html, new RegExp(status));
  assert.match(html, /Currency mismatch/);
  assert.match(html, /Collected \(THB\)/);
  assert.match(html, /Due At/);
});

const bookingDetailData = {
  booking: {
    booking_code: 'TCT-TEST', status: 'Inquiry', customer_name: 'Test Customer', tour_name: 'Test Tour',
    imported_raw_tour_name: null, mapping_status: null, needs_manual_review: false,
    tour_date: null, pickup_time: null, total_guests: 1, guide_language: 'EN', source: 'test',
    pickup_location_name: null, dropoff_location_name: null,
  },
  payment_summary: {
    total_amount: 1000, deposit_amount: null, paid_amount: 0, pending_amount: 0,
    balance_due: 1000, booking_financial_status: 'unpaid', payment_status: 'Unpaid',
    selling_price: 1000, currency: 'THB',
  },
  operations_summary: {
    gross_margin: null, currency: 'THB', cost_status: null, pricing_use: null,
    direct_cost_is_known: null, guide_cost: null, driver_cost: null, other_cost: null,
    total_cost: null, margin_percent: null,
  },
  payments: [],
  assignments: [],
};

test('Booking Detail shows loading/error and unknown deposit with no-payment explanation', () => {
  const props = { data: bookingDetailData, onBack() {}, loading: false, onQuoteGenerated() {} };
  const loading = renderToStaticMarkup(React.createElement(BookingDetail, { ...props, loading: true }));
  const error = renderToStaticMarkup(React.createElement(BookingDetail, { ...props, error: 'Not found' }));
  const empty = renderToStaticMarkup(React.createElement(BookingDetail, props));
  assert.match(loading, /Loading booking detail/);
  assert.match(error, /Unable to load booking financial details/);
  assert.match(empty, /No payment records/);
  assert.match(empty, /No deposit amount is configured/);
  assert.match(empty, /Pending/);
  assert.match(empty, /Unpaid/);
});
