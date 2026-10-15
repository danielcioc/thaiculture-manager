import type { PricingRule, PricingQuote } from '../types/tours';

export const API_BASE = import.meta.env.VITE_API_BASE || 'http://127.0.0.1:8000';

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


export async function getPricingQuotes(): Promise<PricingQuote[]> {
  const response = await fetch(`${API_BASE}/pricing/quotes`);

  if (!response.ok) {
    throw new Error(`Failed to load pricing quotes (${response.status})`);
  }

  return response.json();
}

export async function generatePricingQuote(
  bookingCode: string,
  finalPriceGross?: number,
): Promise<PricingQuote> {
  const response = await fetch(
    `${API_BASE}/pricing/quotes/${encodeURIComponent(bookingCode)}/generate`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(
        finalPriceGross === undefined ? {} : { final_price_gross: finalPriceGross },
      ),
    },
  );

  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(payload.detail || `Failed to generate pricing quote (${response.status})`);
  }

  return payload as PricingQuote;
}

export async function getPricingRules() {
  return apiGet<PricingRule[]>('/pricing/rules');
}

export async function getPricingRuleByTourCode(tourCode: string) {
  return apiGet<PricingRule>(`/pricing/tours/${tourCode}`);
}
