/**
 * SecureNet — HistorySummaryCards
 *
 * Shows total event counts by severity at the top of the History page.
 * Receives the total from the paginated API response.
 */

import { ShieldAlert, AlertTriangle, CheckCircle, Clock } from 'lucide-react';
import styles from './HistorySummaryCards.module.css';

interface HistorySummaryCardsProps {
  total: number | null;
  isLoading: boolean;
}

interface SummaryCardProps {
  label: string;
  value: string | null;
  icon: React.ReactNode;
  variant: 'default' | 'high' | 'medium' | 'low';
}

function SummaryCard({ label, value, icon, variant }: SummaryCardProps) {
  return (
    <div className={`${styles.card} ${styles[variant]}`} role="figure" aria-label={label}>
      <div className={styles.iconWrap} aria-hidden="true">{icon}</div>
      <div className={styles.text}>
        <span className={styles.value}>
          {value ?? <span className={styles.na}>—</span>}
        </span>
        <span className={styles.label}>{label}</span>
      </div>
    </div>
  );
}

export function HistorySummaryCards({ total, isLoading }: HistorySummaryCardsProps) {
  const display = isLoading ? null : total !== null ? total.toLocaleString() : null;

  return (
    <div className={styles.grid} aria-label="Event summary">
      <SummaryCard
        label="Total Events"
        value={display}
        icon={<Clock size={18} />}
        variant="default"
      />
      <SummaryCard
        label="High Severity"
        value={null}
        icon={<ShieldAlert size={18} />}
        variant="high"
      />
      <SummaryCard
        label="Medium Severity"
        value={null}
        icon={<AlertTriangle size={18} />}
        variant="medium"
      />
      <SummaryCard
        label="Resolved"
        value={null}
        icon={<CheckCircle size={18} />}
        variant="low"
      />
    </div>
  );
}
