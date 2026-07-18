export type CustomerListItem = {
  id: string;
  first_name: string | null;
  last_name: string | null;
  display_name: string;
  email: string | null;
  phone: string | null;
  whatsapp: string | null;
  country: string | null;
  nationality: string | null;
  preferred_language: string | null;
  notes: string | null;
  created_at: string;
};

export type CustomersResponse = {
  count: number;
  items: CustomerListItem[];
};
