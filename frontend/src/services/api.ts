import type { PricingRule, PricingQuote } from '../types/tours';

import type { ImportReviewDecisionRequest, ImportReviewDecisionResponse } from '../types/bookings';

export const API_BASE = import.meta.env?.VITE_API_BASE || 'http://127.0.0.1:8000';

export class ApiError extends Error {
  readonly status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
  }
}

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

export async function approveImportReview(
  bookingCode: string,
  request: ImportReviewDecisionRequest,
  bearerToken: string,
): Promise<ImportReviewDecisionResponse> {
  const response = await fetch(
    `${API_BASE}/bookings/${encodeURIComponent(bookingCode)}/import-review/decision`,
    {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${bearerToken}`,
      },
      body: JSON.stringify(request),
    },
  );
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    const detail = typeof payload.detail === 'string' ? payload.detail : '';
    throw new ApiError(detail || `Review approval failed (${response.status})`, response.status);
  }
  return payload as ImportReviewDecisionResponse;
}
