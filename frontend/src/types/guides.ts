export type GuideListItem = {
  id: string;
  name: string;
  phone: string | null;
  line_id: string | null;
  languages: string[] | null;
  license_no: string | null;
  base_area: string | null;
  default_cost: number;
  rating: number | null;
  notes: string | null;
};

export type GuidesResponse = {
  count: number;
  items: GuideListItem[];
};
