import assert from 'node:assert/strict';
import test from 'node:test';
import { paymentListQuery } from '../src/utils/paymentListQuery.ts';

test('payment list sends status and server-side sort parameters', () => {
  assert.equal(paymentListQuery('overdue', 'due_at', 'asc'), '/payments?sort_by=due_at&sort_order=asc&status=overdue');
});

test('all-status view omits the status filter', () => {
  assert.equal(paymentListQuery('all', 'paid_at', 'desc'), '/payments?sort_by=paid_at&sort_order=desc');
});
