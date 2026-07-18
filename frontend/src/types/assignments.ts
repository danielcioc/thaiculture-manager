export type AssignmentListItem = {
  id: string;
  booking_id: string;
  booking_code: string | null;
  assignment_type: string;
  guide_name: string | null;
  driver_name: string | null;
  cost: number;
  status: string;
  notes: string | null;
};

export type AssignmentsResponse = {
  count: number;
  items: AssignmentListItem[];
};
