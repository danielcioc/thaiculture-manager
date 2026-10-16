import assert from 'node:assert/strict';
import test from 'node:test';
import { getBookingFinancialSummaryView } from '../src/utils/bookingFinancialSummary.ts';

test('financial detail view presents total, optional deposit, paid, balance and status', () => {
  assert.deepEqual(getBookingFinancialSummaryView({
    total_amount: 10500,
    deposit_amount: 2500,
    paid_amount: 2500,
    balance_due: 8000,
    booking_financial_status: 'depositpaid',
  }), {
    status: 'depositpaid', total: 10500, deposit: 2500, paid: 2500, balance: 8000,
  });
});

test('unknown deposit stays unset and displayed balance cannot be negative', () => {
  assert.deepEqual(getBookingFinancialSummaryView({
    total_amount: 100,
    deposit_amount: null,
    paid_amount: 150,
    balance_due: 0,
    booking_financial_status: 'paid',
  }), {
    status: 'paid', total: 100, deposit: null, paid: 150, balance: 0,
  });
});
