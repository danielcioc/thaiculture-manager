import assert from 'node:assert/strict';
import { afterEach, test } from 'node:test';
import { ApiError, approveImportReview } from '../src/services/api.ts';

const originalFetch = globalThis.fetch;

afterEach(() => {
  globalThis.fetch = originalFetch;
});

const request = {
  expected_mapping_status: 'probable_manual_review',
  expected_tour_id: null,
  expected_needs_manual_review: true,
  mapping_status: 'confirmed',
  tour_id: 'tour-canonical-id',
  reason: 'Raw label matches the canonical itinerary',
  confirm: true,
  request_id: '123e4567-e89b-42d3-a456-426614174000',
};

test('approval sends the authenticated decision and returns the response', async () => {
  const expected = { booking_code: 'TCT-TEST-1', mapping_status: 'confirmed', replayed: false };
  let captured;
  globalThis.fetch = async (url, options) => {
    captured = { url, options };
    return new Response(JSON.stringify(expected), { status: 200 });
  };

  const result = await approveImportReview('TCT-TEST-1', request, 'test-token');

  assert.deepEqual(result, expected);
  assert.match(captured.url, /\/bookings\/TCT-TEST-1\/import-review\/decision$/);
  assert.equal(captured.options.method, 'POST');
  assert.equal(captured.options.headers.Authorization, 'Bearer test-token');
  assert.deepEqual(JSON.parse(captured.options.body), request);
});

for (const [name, status, detail] of [
  ['permission denied', 403, 'Reviewer permission required'],
  ['stale update', 409, 'Booking mapping changed'],
  ['idempotency payload conflict', 409, 'Request id already used'],
]) {
  test(`approval reports ${name}`, async () => {
    globalThis.fetch = async () => new Response(JSON.stringify({ detail }), { status });

    await assert.rejects(
      approveImportReview('TCT-TEST-1', request, 'test-token'),
      (error) => error instanceof ApiError && error.status === status && error.message === detail,
    );
  });
}
