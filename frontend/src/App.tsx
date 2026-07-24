import { useEffect, useState } from 'react';
import { apiGet, getInvoiceDetail, getInvoices } from './services/api';
import { BookingDetail } from './components/BookingDetail';
import { BookingsList } from './components/BookingsList';
import { CustomersList } from './components/CustomersList';
import { ToursList } from './components/ToursList';
import { AssignmentsList } from './components/AssignmentsList';
import { PaymentsList } from './components/PaymentsList';
import { GuidesList } from './components/GuidesList';
import { DriversList } from './components/DriversList';
import { LocationsList } from './components/LocationsList';
import { InvoicesList } from './components/InvoicesList';
import { InvoiceDetail } from './components/InvoiceDetail';
import type { BookingDetailResponse, BookingsResponse } from './types/bookings';
import type { CustomersResponse } from './types/customers';
import type { ToursResponse } from './types/tours';
import type { AssignmentsResponse } from './types/assignments';
import type { PaymentsResponse } from './types/payments';
import type { GuidesResponse } from './types/guides';
import type { DriversResponse } from './types/drivers';
import type { LocationsResponse } from './types/locations';
import type { InvoiceDetailResponse, InvoicesResponse } from './types/invoices';
import './index.css';
import { formatCurrency } from './utils/formatters';

type View =
  | 'dashboard'
  | 'bookings'
  | 'customers'
  | 'invoices'
  | 'tours'
  | 'assignments'
  | 'payments'
  | 'guides'
  | 'drivers'
  | 'locations';

function App() {
  const [bookings, setBookings] = useState<BookingsResponse | null>(null);
  const [customers, setCustomers] = useState<CustomersResponse | null>(null);
  const [tours, setTours] = useState<ToursResponse | null>(null);
  const [assignments, setAssignments] = useState<AssignmentsResponse | null>(null);
  const [payments, setPayments] = useState<PaymentsResponse | null>(null);
  const [guides, setGuides] = useState<GuidesResponse | null>(null);
  const [drivers, setDrivers] = useState<DriversResponse | null>(null);
  const [locations, setLocations] = useState<LocationsResponse | null>(null);
  const [invoices, setInvoices] = useState<InvoicesResponse | null>(null);

  const [selectedCode, setSelectedCode] = useState<string | null>(null);
  const [detail, setDetail] = useState<BookingDetailResponse | null>(null);

  const [selectedInvoiceNo, setSelectedInvoiceNo] = useState<string | null>(null);
  const [invoiceDetail, setInvoiceDetail] = useState<InvoiceDetailResponse | null>(null);

  const [error, setError] = useState('');
  const [loadingList, setLoadingList] = useState(true);
  const [loadingCustomers, setLoadingCustomers] = useState(true);
  const [loadingTours, setLoadingTours] = useState(true);
  const [loadingAssignments, setLoadingAssignments] = useState(true);
  const [loadingPayments, setLoadingPayments] = useState(true);
  const [loadingGuides, setLoadingGuides] = useState(true);
  const [loadingDrivers, setLoadingDrivers] = useState(true);
  const [loadingLocations, setLoadingLocations] = useState(true);
  const [loadingInvoices, setLoadingInvoices] = useState(true);
  const [loadingDetail, setLoadingDetail] = useState(false);
  const [loadingInvoiceDetail, setLoadingInvoiceDetail] = useState(false);

  const [view, setView] = useState<View>('dashboard');
  const [mobileNavOpen, setMobileNavOpen] = useState(false);

  useEffect(() => {
    apiGet<BookingsResponse>('/bookings')
      .then(setBookings)
      .catch((e) => setError(e.message))
      .finally(() => setLoadingList(false));

    apiGet<CustomersResponse>('/customers')
      .then(setCustomers)
      .catch((e) => setError(e.message))
      .finally(() => setLoadingCustomers(false));

    apiGet<ToursResponse>('/tours')
      .then(setTours)
      .catch((e) => setError(e.message))
      .finally(() => setLoadingTours(false));

    apiGet<AssignmentsResponse>('/assignments')
      .then(setAssignments)
      .catch((e) => setError(e.message))
      .finally(() => setLoadingAssignments(false));

    apiGet<PaymentsResponse>('/payments')
      .then(setPayments)
      .catch((e) => setError(e.message))
      .finally(() => setLoadingPayments(false));

    apiGet<GuidesResponse>('/guides')
      .then(setGuides)
      .catch((e) => setError(e.message))
      .finally(() => setLoadingGuides(false));

    apiGet<DriversResponse>('/drivers')
      .then(setDrivers)
      .catch((e) => setError(e.message))
      .finally(() => setLoadingDrivers(false));

    apiGet<LocationsResponse>('/locations')
      .then(setLocations)
      .catch((e) => setError(e.message))
      .finally(() => setLoadingLocations(false));

    setLoadingInvoices(false);
//     getInvoices()
//       .then((data) => setInvoices(data as InvoicesResponse))
//       .catch((e) => setError(e.message))
//       .finally(() => setLoadingInvoices(false));
  }, []);

  useEffect(() => {
    if (!selectedCode) {
      setDetail(null);
      return;
    }

    setLoadingDetail(true);
    apiGet<BookingDetailResponse>(`/bookings/${selectedCode}/full`)
      .then(setDetail)
      .catch((e) => setError(e.message))
      .finally(() => setLoadingDetail(false));
  }, [selectedCode]);

  useEffect(() => {
    if (!selectedInvoiceNo) {
      setInvoiceDetail(null);
      return;
    }

    setLoadingInvoiceDetail(true);
    getInvoiceDetail(selectedInvoiceNo)
      .then((data) => setInvoiceDetail(data as InvoiceDetailResponse))
      .catch((e) => setError(e.message))
      .finally(() => setLoadingInvoiceDetail(false));
  }, [selectedInvoiceNo]);

  if (loadingList) {
    return <div className="page">Loading ThaiCulture Manager...</div>;
  }

  if (error) {
    return <div className="page">Error: {error}</div>;
  }

  if (!bookings) {
    return <div className="page">No booking data available</div>;
  }

  const isDetailView = Boolean(selectedCode);
  const isInvoiceDetailView = Boolean(selectedInvoiceNo);

  const totalBookings = bookings.items.length;
  const confirmedBookings = bookings.items.filter(
    (item) => item.status === 'Confirmed',
  ).length;
  const unconfirmedBookings = totalBookings - confirmedBookings;
  const totalGuests = bookings.items.reduce(
    (sum, item) => sum + Number(item.total_guests || 0),
    0,
  );
  const totalRevenue = bookings.items.reduce(
    (sum, item) => sum + Number(item.selling_price || 0),
    0,
  );
  const currency = bookings.items[0]?.currency ?? 'THB';

  const goToView = (nextView: View) => {
    setSelectedCode(null);
    setSelectedInvoiceNo(null);
    setView(nextView);
    setMobileNavOpen(false);
  };

  const renderContent = () => {
    if (view === 'bookings') {
      return !isDetailView ? (
        <BookingsList data={bookings} onSelectBooking={setSelectedCode} />
      ) : detail ? (
        <BookingDetail data={detail} loading={loadingDetail} onBack={() => setSelectedCode(null)} />
      ) : (
        <div className="panel">Loading booking detail...</div>
      );
    }

    if (view === 'customers') {
      if (loadingCustomers) return <section className="panel">Loading customers...</section>;
      if (!customers) return <section className="panel">No customer data available.</section>;
      return <CustomersList data={customers} />;
    }

    if (view === 'invoices') {
      if (loadingInvoices) return <section className="panel">Loading invoices...</section>;
      if (!invoices) return <section className="panel">No invoice data available.</section>;

      return !isInvoiceDetailView ? (
        <InvoicesList data={invoices} onSelectInvoice={setSelectedInvoiceNo} />
      ) : invoiceDetail ? (
        <InvoiceDetail
          data={invoiceDetail}
          loading={loadingInvoiceDetail}
          onBack={() => setSelectedInvoiceNo(null)}
        />
      ) : (
        <div className="panel">Loading invoice detail...</div>
      );
    }

    if (view === 'tours') {
      if (loadingTours) return <section className="panel">Loading tours...</section>;
      if (!tours) return <section className="panel">No tour data available.</section>;
      return <ToursList data={tours} />;
    }

    if (view === 'assignments') {
      if (loadingAssignments) return <section className="panel">Loading assignments...</section>;
      if (!assignments) return <section className="panel">No assignment data available.</section>;
      return <AssignmentsList data={assignments} />;
    }

    if (view === 'payments') {
      if (loadingPayments) return <section className="panel">Loading payments...</section>;
      if (!payments) return <section className="panel">No payment data available.</section>;
      return <PaymentsList data={payments} />;
    }

    if (view === 'guides') {
      if (loadingGuides) return <section className="panel">Loading guides...</section>;
      if (!guides) return <section className="panel">No guide data available.</section>;
      return <GuidesList data={guides} />;
    }

    if (view === 'drivers') {
      if (loadingDrivers) return <section className="panel">Loading drivers...</section>;
      if (!drivers) return <section className="panel">No driver data available.</section>;
      return <DriversList data={drivers} />;
    }

    if (view === 'locations') {
      if (loadingLocations) return <section className="panel">Loading locations...</section>;
      if (!locations) return <section className="panel">No location data available.</section>;
      return <LocationsList data={locations} />;
    }

    return (
      <>
        <div className="grid">
          <button type="button" className="card card-button" onClick={() => goToView('bookings')}>
            <span>Total Bookings</span>
            <strong>{totalBookings}</strong>
          </button>

          <button type="button" className="card card-button" onClick={() => goToView('bookings')}>
            <span>Confirmed</span>
            <strong>{confirmedBookings}</strong>
          </button>

          <button type="button" className="card card-button" onClick={() => goToView('bookings')}>
            <span>Unconfirmed</span>
            <strong>{unconfirmedBookings}</strong>
          </button>

          <button type="button" className="card card-button" onClick={() => goToView('bookings')}>
            <span>Total Guests</span>
            <strong>{totalGuests}</strong>
          </button>

          <button type="button" className="card card-button" onClick={() => goToView('payments')}>
            <span>Total Revenue</span>
            <strong>{formatCurrency(totalRevenue, currency)}</strong>
          </button>

          <div className="card">
            <span>Total Invoices</span>
            <strong>{invoices?.count ?? 0}</strong>
          </div>
        </div>
      </>
    );
  };

  return (
    <div className="page">
      <header className="app-header">
        <div className="app-header-top">
          <div className="app-header-copy">
            <p className="app-kicker">
              {isDetailView ? 'Booking Detail' : isInvoiceDetailView ? 'Invoice Detail' : 'Operations Dashboard'}
            </p>
            <h1>ThaiCulture Manager</h1>
            <p className="section-subtitle">
              {isDetailView
                ? selectedCode
                : isInvoiceDetailView
                  ? selectedInvoiceNo
                  : view[0].toUpperCase() + view.slice(1)}
            </p>
          </div>

          <button
            type="button"
            className="mobile-nav-trigger"
            aria-expanded={mobileNavOpen}
            aria-controls="mobile-sections"
            onClick={() => setMobileNavOpen((value) => !value)}
          >
            <span>Sections</span>
            <span>{mobileNavOpen ? 'Close' : 'Open'}</span>
          </button>
        </div>

        <nav className="tabs tabs-desktop" aria-label="Primary sections">
          {(['dashboard', 'bookings', 'customers', 'invoices', 'tours', 'assignments', 'payments', 'guides', 'drivers', 'locations'] as View[]).map((item) => (
            <button
              key={item}
              type="button"
              className={view === item ? 'tab active' : 'tab'}
              onClick={() => goToView(item)}
            >
              {item[0].toUpperCase() + item.slice(1)}
            </button>
          ))}
        </nav>

        {mobileNavOpen && (
          <div className="mobile-nav-drawer" id="mobile-sections">
            {(['dashboard', 'bookings', 'customers', 'invoices', 'tours', 'assignments', 'payments', 'guides', 'drivers', 'locations'] as View[]).map((item) => (
              <button
                key={item}
                type="button"
                className={view === item ? 'mobile-nav-item active' : 'mobile-nav-item'}
                onClick={() => {
                  setView(item);
                  setSelectedCode(null);
                  setSelectedInvoiceNo(null);
                  setMobileNavOpen(false);
                }}
              >
                {item[0].toUpperCase() + item.slice(1)}
              </button>
            ))}
          </div>
        )}
      </header>

      {renderContent()}
    </div>
  );
}

export default App;
