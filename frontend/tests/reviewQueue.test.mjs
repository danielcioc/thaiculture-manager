import assert from 'node:assert/strict';
import test from 'node:test';
import {
  classifyReviewConflict,
  countPendingReviews,
  getReviewQueuePage,
} from '../src/utils/reviewQueue.ts';

const booking = (overrides = {}) => ({
  id: 'booking-1',
  booking_code: 'TCT-001',
  status: 'Inquiry',
  source: 'import',
  customer_name: 'Test Customer',
  customer_email: null,
  customer_country: null,
  tour_id: null,
  tour_code: null,
  tour_name: null,
  tour_category: null,
  tour_duration_hours: null,
  pickup_location_name: null,
  pickup_location_address: null,
  pickup_google_maps_url: null,
  dropoff_location_name: null,
  dropoff_location_address: null,
  dropoff_google_maps_url: null,
  tour_date: '2026-11-10',
  pickup_time: null,
  adults: 1,
  children: 0,
  infants: 0,
  total_guests: 1,
  guide_language: null,
  selling_price: 1000,
  currency: 'THB',
  imported_raw_tour_name: 'Imported tour label',
  mapping_status: 'probable_manual_review',
  needs_manual_review: true,
  created_at: '2026-10-01T12:00:00Z',
  ...overrides,
});

const filters = (overrides = {}) => ({
  mappingStatus: 'all',
  needsManualReview: 'true',
  bookingStatus: 'all',
  sortBy: 'created_desc',
  page: 1,
  pageSize: 10,
  ...overrides,
});

test('filters by mapping status, review flag and booking status', () => {
  const bookings = [
    booking(),
    booking({ id: 'booking-2', booking_code: 'TCT-002', mapping_status: 'unmapped' }),
    booking({ id: 'booking-3', booking_code: 'TCT-003', mapping_status: 'confirmed', needs_manual_review: false, status: 'Confirmed' }),
  ];

  const filtered = getReviewQueuePage(bookings, filters({
    mappingStatus: 'unmapped',
    bookingStatus: 'Inquiry',
  }));
  const confirmed = getReviewQueuePage(bookings, filters({
    needsManualReview: 'false',
    bookingStatus: 'Confirmed',
  }));

  assert.deepEqual(filtered.items.map((item) => item.booking_code), ['TCT-002']);
  assert.deepEqual(confirmed.items.map((item) => item.booking_code), ['TCT-003']);
  assert.equal(countPendingReviews(bookings), 2);
});

test('sorts and paginates without duplicates between pages', () => {
  const bookings = [
    booking({ id: 'booking-1', booking_code: 'TCT-003', tour_date: '2026-11-12' }),
    booking({ id: 'booking-2', booking_code: 'TCT-001', tour_date: '2026-11-10' }),
    booking({ id: 'booking-3', booking_code: 'TCT-002', tour_date: '2026-11-11' }),
  ];

  const first = getReviewQueuePage(bookings, filters({ sortBy: 'tour_date_asc', pageSize: 2 }));
  const second = getReviewQueuePage(bookings, filters({ sortBy: 'tour_date_asc', pageSize: 2, page: 2 }));

  assert.deepEqual(first.items.map((item) => item.booking_code), ['TCT-001', 'TCT-002']);
  assert.deepEqual(second.items.map((item) => item.booking_code), ['TCT-003']);
  assert.equal(first.pageCount, 2);
  assert.equal(new Set([...first.items, ...second.items].map((item) => item.id)).size, 3);
});

test('classifies stale and reused-request conflicts distinctly', () => {
  assert.equal(classifyReviewConflict('Booking mapping changed; reload before retrying'), 'stale');
  assert.equal(classifyReviewConflict('This actor/request_id pair was already used with a different payload'), 'request_id_reuse');
  assert.equal(classifyReviewConflict('Current mapping metadata is inconsistent'), 'other');
});
