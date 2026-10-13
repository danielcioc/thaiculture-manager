export type TourListItem = {
  id: string;
  tour_code: string;
  name: string;
  category: string | null;
  default_duration_hours: number | null;
  website_url: string | null;
  is_active: boolean;
};

export type ToursResponse = {
  count: number;
  items: TourListItem[];
};

export type PricingRule = {
  rule_name: string;
  tour_id: string;
  tour_code: string;
  tour_name: string;
  rule_type: string;
  confidence_status: string | null;
  pricing_use: string | null;
  cost_status: string | null;
  requires_manual_review: boolean | null;
  currency: string | null;
  selling_price_gross: number | null;
  selling_price_net: number | null;
  vat_rate: number | null;
  direct_cost_total: number | null;
  insurance_rule: string | null;
  includes: string | null;
  excludes: string | null;
  conditions: Record<string, unknown>;
  calculation: Record<string, unknown>;
  is_active: boolean;
};
