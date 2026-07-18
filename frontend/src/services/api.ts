export const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000';

export async function apiGet<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`);

  if (!response.ok) {
    throw new Error(`API request failed: ${response.status} at ${path}`);
  }

  return response.json();
}

export async function getInvoices() {
  return apiGet('/invoices');
}

export async function getInvoiceDetail(invoiceNo: string) {
  return apiGet(`/invoices/${invoiceNo}`);
}
