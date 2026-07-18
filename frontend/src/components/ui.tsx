import type { ReactNode } from 'react';

type StatCardProps = {
  label: string;
  value: ReactNode;
};

export function StatCard({ label, value }: StatCardProps) {
  return (
    <div className="card">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

type SectionHeaderProps = {
  title: string;
  subtitle: string;
  pill?: ReactNode;
};

export function SectionHeader({ title, subtitle, pill }: SectionHeaderProps) {
  return (
    <div className="section-header">
      <div>
        <h2 style={{ margin: 0 }}>{title}</h2>
        <p className="section-subtitle">{subtitle}</p>
      </div>
      {pill ? pill : null}
    </div>
  );
}

type DetailItemProps = {
  label: string;
  value: ReactNode;
};

export function DetailItem({ label, value }: DetailItemProps) {
  return (
    <div>
      <span className="tour-meta-label">{label}</span>
      <span className="tour-meta-value">{value}</span>
    </div>
  );
}
