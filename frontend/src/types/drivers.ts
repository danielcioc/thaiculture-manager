export type DriverListItem = {
  id: string;
  name: string;
  phone: string | null;
  line_id: string | null;
  base_area: string | null;
  default_cost: number;
  rating: number | null;
};

export type DriversResponse = {
  count: number;
  items: DriverListItem[];
};
