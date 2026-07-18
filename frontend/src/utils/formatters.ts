export function formatCurrency(
  value: number | string | null | undefined,
  currency = 'THB',
) {
  if (value === null || value === undefined || value === '') return '-';

  const amount = Number(value);
  if (Number.isNaN(amount)) return '-';

  return new Intl.NumberFormat('en-US', {
    maximumFractionDigits: 0,
  }).format(amount) + ` ${currency}`;
}

export function formatDate(value: string | null | undefined) {
  if (!value) return '-';

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;

  return new Intl.DateTimeFormat('en-GB', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
  }).format(date);
}

export function formatDateTime(value: string | null | undefined) {
  if (!value) return '-';

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;

  return new Intl.DateTimeFormat('en-GB', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  }).format(date);
}

export function formatTime(value: string | null | undefined) {
  if (!value) return '-';

  const normalized = `1970-01-01T${value}`;
  const date = new Date(normalized);
  if (Number.isNaN(date.getTime())) return value;

  return new Intl.DateTimeFormat('en-GB', {
    hour: '2-digit',
    minute: '2-digit',
  }).format(date);
}

export function formatDurationHours(value: number | string | null | undefined) {
  if (value === null || value === undefined || value === '') return '-';

  const hours = Number(value);
  if (Number.isNaN(hours)) return '-';

  if (Number.isInteger(hours)) {
    return `${hours}h`;
  }

  return `${hours.toFixed(1)}h`;
}
