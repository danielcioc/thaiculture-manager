import assert from 'node:assert/strict';
import test from 'node:test';
import { dashboardFinancialCards } from '../src/utils/dashboardFinancialCards.ts';

test('dashboard presents the canonical financial status counts', () => {
  const cards = dashboardFinancialCards({ financial_kpis: {
    unpaid: 1, depositrequested: 2, depositpaid: 3, partiallypaid: 4, paid: 5, overdue: 6,
    total_outstanding: 987.5,
  } });
  assert.deepEqual(cards.map(({ key, value }) => [key, value]), [
    ['unpaid', 1], ['depositrequested', 2], ['depositpaid', 3], ['partiallypaid', 4], ['paid', 5],
    ['overdue', 6], ['total_outstanding', 987.5],
  ]);
  assert.match(cards.at(-1).definition, /all bookings/);
});

test('empty dashboard financial data renders zero values', () => {
  const cards = dashboardFinancialCards({ financial_kpis: {
    unpaid: 0, depositrequested: 0, depositpaid: 0, partiallypaid: 0, paid: 0, overdue: 0,
    total_outstanding: 0,
  } });
  assert.ok(cards.every((card) => card.value === 0));
});
