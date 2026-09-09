/**
 * SecureNet — ReportSummaryCards
 *
 * Three KPI cards for the Reports page summary row.
 * Shows "Not available" for null values (backend not connected).
 */

import { FileText, Clock, Calendar } from 'lucide-react';
import type { ReportSummary } from '../../types/reports.types';
import { Card } from '../common/Card';
import { Spinner } from '../common/LoadingState';
import styles from './ReportSummaryCards.module.css';

interface ReportSummaryCardsProps {
  data: ReportSummary | null;
  isLoading: boolean;
}

interface SummaryCardProps {
  icon: React.ReactNode;
  label: string;
  value: number | null;
  isLoading: boolean;
}

function SummaryCard({ icon, label, value, isLoading }: SummaryCardProps) {
  return (
    <Card padding="md" className={styles.card}>
      <div className={styles.iconWrap} aria-hidden="true">{icon}</div>
      <div className={styles.body}>
        <p className={styles.label}>{label}</p>
        <p className={styles.value}>
          {isLoading
            ? <Spinner size="sm" />
            : value !== null
              ? value.toLocaleString()
              : <span className={styles.na}>Not available</span>
          }
        </p>
      </div>
    </Card>
  );
}

export function ReportSummaryCards({ data, isLoading }: ReportSummaryCardsProps) {
  return (
    <div className={styles.grid}>
      <SummaryCard
        icon={<FileText size={18} />}
        label="Total Reports"
        value={data?.totalReports ?? null}
        isLoading={isLoading}
      />
      <SummaryCard
        icon={<Clock size={18} />}
        label="Last 7 Days"
        value={data?.recentReportsCount ?? null}
        isLoading={isLoading}
      />
      <SummaryCard
        icon={<Calendar size={18} />}
        label="Generated This Month"
        value={data?.generatedThisMonth ?? null}
        isLoading={isLoading}
      />
    </div>
  );
}
