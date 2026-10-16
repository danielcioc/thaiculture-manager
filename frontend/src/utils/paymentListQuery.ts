export type PaymentSortField = 'paid_at' | 'due_at';
export type PaymentSortOrder = 'asc' | 'desc';

export function paymentListQuery(status: string, sortBy: PaymentSortField, sortOrder: PaymentSortOrder) {
  const params = new URLSearchParams({ sort_by: sortBy, sort_order: sortOrder });
  if (status !== 'all') params.set('status', status);
  return `/payments?${params.toString()}`;
}
