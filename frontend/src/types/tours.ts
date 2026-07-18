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
