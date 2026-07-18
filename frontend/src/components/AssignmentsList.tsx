import type { AssignmentsResponse } from '../types/assignments';
import { formatCurrency } from '../utils/formatters';
import { getStatusClass } from '../utils/status';
import { DetailItem, SectionHeader, StatCard } from './ui';

type AssignmentsListProps = {
  data: AssignmentsResponse;
};

export function AssignmentsList({ data }: AssignmentsListProps) {
  const guideCount = data.items.filter(
    (item) => item.assignment_type.toLowerCase() === 'guide',
  ).length;
  const driverCount = data.items.filter(
    (item) => item.assignment_type.toLowerCase() === 'driver',
  ).length;
  const assignedCount = data.items.filter(
    (item) => item.status.toLowerCase() === 'assigned',
  ).length;
  const totalCost = data.items.reduce(
    (sum, item) => sum + Number(item.cost || 0),
    0,
  );

  return (
    <>
      <div className="grid">
        <StatCard label="Total Assignments" value={data.count} />

        <StatCard label="Guides" value={guideCount} />

        <StatCard label="Drivers" value={driverCount} />

        <StatCard label="Total Cost" value={formatCurrency(totalCost, 'THB')} />
      </div>

      <section className="panel">
        <SectionHeader
          title="Assignments"
          subtitle="Operational resource assignments"
          pill={
            <span className={`meta-pill ${getStatusClass(assignedCount === data.count ? 'assigned' : 'pending')}`}>
              {assignedCount === data.count ? 'All Assigned' : `${assignedCount} Assigned`}
            </span>
          }
        />

        {data.items.length === 0 ? (
          <p>No assignments found.</p>
        ) : (
          <div className="assignment-list-page">
            {data.items.map((assignment) => {
              const assignedPerson =
                assignment.assignment_type.toLowerCase() === 'guide'
                  ? assignment.guide_name || '-'
                  : assignment.driver_name || '-';

              return (
                <article className="assignment-row interactive-card" key={assignment.id}>
                  <div className="assignment-row-top">
                    <div>
                      <div className="assignment-title-row">
                        <div className="assignment-name">
                          {assignment.assignment_type.charAt(0).toUpperCase() +
                            assignment.assignment_type.slice(1)}
                        </div>
                        <div className="assignment-secondary">
                          {assignment.booking_code || 'No booking code'}
                        </div>
                      </div>
                    </div>
                    <span className={`status ${getStatusClass(assignment.status)}`}>
                      {assignment.status.charAt(0).toUpperCase() + assignment.status.slice(1)}
                    </span>
                  </div>

                  <div className="assignment-page-grid">
                    <DetailItem label="Assigned To" value={assignedPerson} />

                    <DetailItem
                      label="Type"
                      value={assignment.assignment_type.charAt(0).toUpperCase() + assignment.assignment_type.slice(1)}
                    />

                    <DetailItem label="Cost" value={formatCurrency(assignment.cost, 'THB')} />
                  </div>

                  <div className="tour-notes">
                    <span className="tour-meta-label">Notes</span>
                    <p>{assignment.notes || '-'}</p>
                  </div>
                </article>
              );
            })}
          </div>
        )}
      </section>
    </>
  );
}
