import { useCallback, useEffect, useState } from 'react';
import type { FormEvent } from 'react';
import { ApiError, apiGet, approveImportReview } from '../services/api';
import type {
  BookingListItem,
  BookingsResponse,
  ImportReviewDecisionRequest,
} from '../types/bookings';
import type { TourListItem, ToursResponse } from '../types/tours';
import {
  classifyReviewConflict,
  countPendingReviews,
  getReviewQueuePage,
  type ReviewQueueFilters,
} from '../utils/reviewQueue';

function formatMappingStatus(value: string | null) {
  return value ? value.replace(/_/g, ' ') : 'Not set';
}

export function ImportReviewQueue() {
  const [bookings, setBookings] = useState<BookingListItem[]>([]);
  const [tours, setTours] = useState<TourListItem[]>([]);
  const [selectedCode, setSelectedCode] = useState('');
  const [selectedTourId, setSelectedTourId] = useState('');
  const [reason, setReason] = useState('');
  const [confirmed, setConfirmed] = useState(false);
  const [requestId, setRequestId] = useState('');
  const [reviewerToken, setReviewerToken] = useState('');
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [requiresReload, setRequiresReload] = useState(false);
  const [mappingFilter, setMappingFilter] = useState<ReviewQueueFilters['mappingStatus']>('all');
  const [reviewFlagFilter, setReviewFlagFilter] = useState<ReviewQueueFilters['needsManualReview']>('true');
  const [bookingStatusFilter, setBookingStatusFilter] = useState('all');
  const [sortBy, setSortBy] = useState<ReviewQueueFilters['sortBy']>('created_desc');
  const [page, setPage] = useState(1);
  const pageSize = 10;

  const reload = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const [bookingData, tourData] = await Promise.all([
        apiGet<BookingsResponse>('/bookings'),
        apiGet<ToursResponse>('/tours'),
      ]);
      setBookings(bookingData.items);
      setTours(tourData.items.filter((tour) => tour.is_active));
      setRequiresReload(false);
      if (selectedCode && !bookingData.items.some((item) => item.booking_code === selectedCode)) {
        setSelectedCode('');
        setSelectedTourId('');
        setReason('');
        setConfirmed(false);
        setRequestId('');
        setRequiresReload(false);
      }
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : 'Unable to load review queue.');
    } finally {
      setLoading(false);
    }
  }, [selectedCode]);

  useEffect(() => {
    void reload();
  }, [reload]);

  const selectedBooking = bookings.find((booking) => booking.booking_code === selectedCode);
  const queuePage = getReviewQueuePage(bookings, {
    mappingStatus: mappingFilter,
    needsManualReview: reviewFlagFilter,
    bookingStatus: bookingStatusFilter,
    sortBy,
    page,
    pageSize,
  });
  const pendingReviewCount = countPendingReviews(bookings);
  const bookingStatuses = [...new Set(bookings.map((booking) => booking.status))].sort();
  const invalidateRetryKey = () => setRequestId('');
  const updateFilter = (update: () => void) => {
    update();
    setPage(1);
  };

  const submitApproval = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!selectedBooking || !selectedTourId || !reviewerToken.trim() || !reason.trim() || !confirmed) {
      setError('Choose a canonical tour, provide a reviewer token and reason, then confirm the decision.');
      return;
    }

    const currentRequestId = requestId || crypto.randomUUID();
    setRequestId(currentRequestId);
    setSubmitting(true);
    setError('');
    setSuccess('');

    const request: ImportReviewDecisionRequest = {
      expected_mapping_status: selectedBooking.mapping_status ?? 'unmapped',
      expected_tour_id: selectedBooking.tour_id,
      expected_needs_manual_review: selectedBooking.needs_manual_review === true,
      mapping_status: 'confirmed',
      tour_id: selectedTourId,
      reason: reason.trim(),
      confirm: true,
      request_id: currentRequestId,
    };

    try {
      const result = await approveImportReview(selectedBooking.booking_code, request, reviewerToken.trim());
      setSuccess(
        `${result.booking_code} approved${result.replayed ? ' (safe retry)' : ''}; operational booking status remains ${result.status}.`,
      );
      setSelectedCode('');
      setSelectedTourId('');
      setReason('');
      setConfirmed(false);
      setRequestId('');
      await reload();
    } catch (submitError) {
      if (submitError instanceof ApiError && submitError.status === 403) {
        setError('Permission denied. The authenticated reviewer needs bookings.import_review.approve.');
      } else if (submitError instanceof ApiError && submitError.status === 409) {
        setRequestId('');
        setRequiresReload(true);
        const conflict = classifyReviewConflict(submitError.message);
        const explanation = conflict === 'stale'
          ? 'This booking changed after the queue loaded.'
          : conflict === 'request_id_reuse'
            ? 'This request ID was already used for a different decision payload.'
            : 'The server rejected this decision because the review state conflicts.';
        setError(`${explanation} Reload the queue and verify the current mapping before deciding again.`);
      } else {
        setError(submitError instanceof Error ? submitError.message : 'Approval failed. You can retry unchanged input safely.');
      }
    } finally {
      setSubmitting(false);
    }
  };

  const chooseBooking = (booking: BookingListItem) => {
    setSelectedCode(booking.booking_code);
    setSelectedTourId('');
    setReason('');
    setConfirmed(false);
    setRequestId('');
    setError('');
    setSuccess('');
    setRequiresReload(false);
  };

  return (
    <section className="panel review-queue">
      <div className="section-header">
        <div>
          <h2 style={{ margin: 0 }}>Importer review queue</h2>
          <p className="section-subtitle">Read-only source metadata with explicit, audited mapping approval.</p>
        </div>
        <button type="button" className="tab" onClick={() => void reload()} disabled={loading}>
          Refresh queue
        </button>
      </div>

      <label className="review-token-field">
        Reviewer bearer token (kept in memory only)
        <input
          type="password"
          autoComplete="off"
          value={reviewerToken}
          onChange={(event) => setReviewerToken(event.target.value)}
          placeholder="Paste a trusted issuer token for this session"
        />
      </label>

      {loading ? <p>Loading review queue…</p> : null}
      <div className="review-queue-summary">
        <span className="status needs-review">{pendingReviewCount} pending review</span>
        <span>{queuePage.total} matching bookings</span>
      </div>

      <div className="review-queue-filters" aria-label="Review queue filters">
        <label>
          Mapping status
          <select value={mappingFilter} onChange={(event) => updateFilter(() => setMappingFilter(event.target.value as ReviewQueueFilters['mappingStatus']))}>
            <option value="all">All mappings</option>
            <option value="confirmed">Confirmed</option>
            <option value="probable_manual_review">Probable manual review</option>
            <option value="unmapped">Unmapped</option>
          </select>
        </label>
        <label>
          Manual review
          <select value={reviewFlagFilter} onChange={(event) => updateFilter(() => setReviewFlagFilter(event.target.value as ReviewQueueFilters['needsManualReview']))}>
            <option value="true">Needs review</option>
            <option value="false">No review needed</option>
            <option value="all">All flags</option>
          </select>
        </label>
        <label>
          Booking status
          <select value={bookingStatusFilter} onChange={(event) => updateFilter(() => setBookingStatusFilter(event.target.value))}>
            <option value="all">All statuses</option>
            {bookingStatuses.map((status) => <option key={status} value={status}>{status}</option>)}
          </select>
        </label>
        <label>
          Sort by
          <select value={sortBy} onChange={(event) => updateFilter(() => setSortBy(event.target.value as ReviewQueueFilters['sortBy']))}>
            <option value="created_desc">Recently created</option>
            <option value="tour_date_asc">Tour date</option>
            <option value="booking_code_asc">Booking code</option>
          </select>
        </label>
      </div>

      {!loading && queuePage.total === 0 ? <p>No bookings match these review filters.</p> : null}

      <div className="review-queue-list">
        {queuePage.items.map((booking) => (
          <article className="review-queue-item" key={booking.id}>
            <button
              type="button"
              className="review-booking-select"
              aria-expanded={selectedCode === booking.booking_code}
              onClick={() => chooseBooking(booking)}
            >
              <span>
                <strong>{booking.booking_code}</strong>
                <small>{booking.customer_name || 'Customer unavailable'} · booking status: {booking.status}</small>
              </span>
              <span className="status needs-review">{formatMappingStatus(booking.mapping_status)}</span>
            </button>
            <div className="import-review-metadata">
              <span className="imported-tour-label">Raw tour label: {booking.imported_raw_tour_name || 'Not available'}</span>
              <span className="imported-tour-label">
                Current canonical tour: {booking.tour_name || 'None — needs review'}
              </span>
            </div>

            {selectedCode === booking.booking_code && (
              <form className="review-approval-form" onSubmit={submitApproval}>
                <fieldset disabled={requiresReload}>
                <label>
                  Candidate canonical tour
                  <select
                    required
                    value={selectedTourId}
                    onChange={(event) => { setSelectedTourId(event.target.value); invalidateRetryKey(); }}
                  >
                    <option value="">Select an active canonical tour</option>
                    {tours.map((tour) => (
                      <option value={tour.id} key={tour.id}>{tour.tour_code} · {tour.name}</option>
                    ))}
                  </select>
                </label>
                {tours.length === 0 && <p role="alert">No active canonical tours are available.</p>}
                <label>
                  Correction reason
                  <textarea
                    required
                    minLength={1}
                    value={reason}
                    onChange={(event) => { setReason(event.target.value); invalidateRetryKey(); }}
                    placeholder="Explain why this canonical tour matches the imported label"
                  />
                </label>
                <label className="review-confirmation">
                  <input
                    type="checkbox"
                    checked={confirmed}
                    onChange={(event) => { setConfirmed(event.target.checked); invalidateRetryKey(); }}
                  />
                  I confirm this canonical tour mapping for the raw imported label.
                </label>
                {requestId && <p className="review-request-id">Request ID for safe retry: <code>{requestId}</code></p>}
                <button
                  type="submit"
                  className="tab active"
                  disabled={submitting || !reviewerToken.trim() || !selectedTourId || !reason.trim() || !confirmed || tours.length === 0}
                >
                  {submitting ? 'Submitting…' : requestId ? 'Retry same decision safely' : 'Approve mapping'}
                </button>
                <p className="section-subtitle">A failed request can be retried unchanged with the same request ID. Changing the decision starts a new request.</p>
                </fieldset>
                {requiresReload && (
                  <button type="button" className="tab" onClick={() => void reload()} disabled={loading}>
                    Reload before retry
                  </button>
                )}
              </form>
            )}
          </article>
        ))}
      </div>
      <div className="review-pagination" aria-label="Review queue pages">
        <button type="button" className="tab" onClick={() => setPage((current) => Math.max(1, current - 1))} disabled={queuePage.page <= 1}>
          Previous
        </button>
        <span>Page {queuePage.page} of {queuePage.pageCount}</span>
        <button type="button" className="tab" onClick={() => setPage((current) => Math.min(queuePage.pageCount, current + 1))} disabled={queuePage.page >= queuePage.pageCount}>
          Next
        </button>
      </div>
      {error && <p role="alert" className="review-feedback review-feedback-error">{error}</p>}
      {success && <p role="status" className="review-feedback review-feedback-success">{success}</p>}
    </section>
  );
}
