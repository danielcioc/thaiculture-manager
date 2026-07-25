export function getStatusClass(value: string | null | undefined) {
  const normalized = (value || '').trim().toLowerCase();

  if (!normalized) return 'status-neutral';
  if (['confirmed', 'paid', 'active', 'completed', 'depositpaid'].includes(normalized)) {
    return 'status-positive';
  }
  if (['pending', 'partially paid', 'partiallypaid', 'depositrequested', 'in progress'].includes(normalized)) {
    return 'status-warning';
  }
  if (['cancelled', 'canceled', 'inactive', 'failed', 'unpaid'].includes(normalized)) {
    return 'status-negative';
  }

  return 'status-neutral';
}
