import type { BookingListItem, MappingStatus } from '../types/bookings';

export type ReviewQueueFilters = {
  mappingStatus: 'all' | MappingStatus;
  needsManualReview: 'all' | 'true' | 'false';
  bookingStatus: 'all' | string;
  sortBy: 'created_desc' | 'tour_date_asc' | 'booking_code_asc';
  page: number;
  pageSize: number;
};

export type ReviewQueuePage = {
  items: BookingListItem[];
  total: number;
  page: number;
  pageCount: number;
};

export function countPendingReviews(bookings: BookingListItem[]) {
  return bookings.filter((booking) => booking.needs_manual_review === true).length;
}

export function getReviewQueuePage(
  bookings: BookingListItem[],
  filters: ReviewQueueFilters,
): ReviewQueuePage {
  const filtered = bookings.filter((booking) => {
    if (filters.mappingStatus !== 'all' && booking.mapping_status !== filters.mappingStatus) return false;
    if (filters.bookingStatus !== 'all' && booking.status !== filters.bookingStatus) return false;
    if (filters.needsManualReview !== 'all') {
      const expected = filters.needsManualReview === 'true';
      if (booking.needs_manual_review !== expected) return false;
    }
    return true;
  });

  filtered.sort((left, right) => {
    if (filters.sortBy === 'booking_code_asc') {
      return left.booking_code.localeCompare(right.booking_code);
    }
    if (filters.sortBy === 'tour_date_asc') {
      const leftDate = left.tour_date || '9999-12-31';
      const rightDate = right.tour_date || '9999-12-31';
      return leftDate.localeCompare(rightDate) || left.booking_code.localeCompare(right.booking_code);
    }
    return right.created_at.localeCompare(left.created_at)
      || left.booking_code.localeCompare(right.booking_code);
  });

  const pageSize = Math.max(1, filters.pageSize);
  const pageCount = Math.max(1, Math.ceil(filtered.length / pageSize));
  const page = Math.min(Math.max(1, filters.page), pageCount);
  const start = (page - 1) * pageSize;

  return { items: filtered.slice(start, start + pageSize), total: filtered.length, page, pageCount };
}

export function classifyReviewConflict(message: string): 'stale' | 'request_id_reuse' | 'other' {
  if (message.toLowerCase().includes('booking mapping changed')) return 'stale';
  if (message.toLowerCase().includes('already used with a different payload')) return 'request_id_reuse';
  return 'other';
}
