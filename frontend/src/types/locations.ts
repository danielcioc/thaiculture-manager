export type LocationListItem = {
  id: string;
  name: string;
  address: string | null;
  google_maps_url: string | null;
  city: string | null;
  country: string;
};

export type LocationsResponse = {
  count: number;
  items: LocationListItem[];
};
