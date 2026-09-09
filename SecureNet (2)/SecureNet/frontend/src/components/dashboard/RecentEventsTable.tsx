/**
 * SecureNet — RecentEventsTable
 *
 * Shows the most recent security events on the Dashboard.
 * Empty state until backend provides data. No invented values.
 *
 * Columns: Time | Source | Destination | Score | Severity | Attack Type | Mode | State | Action
 */

import { Link } from 'react-router-dom';
import { ArrowRight } from 'lucide-react';
import type { SecurityEvent } from '../../types/security.types';
import { SeverityBadge } from '../common/SeverityBadge';
import { StatusBadge } from '../common/StatusBadge';
import { ModeBadge } from '../common/ModeBadge';
import { EmptyState } from '../common/EmptyState';
import { LoadingState } from '../common/LoadingState';
import { formatTimestamp, formatScore } from '../../utils/format';
import styles from './RecentEventsTable.module.css';

interface RecentEventsTableProps {
  events: SecurityEvent[];
  isLoading: boolean;
}

export function RecentEventsTable({ events, isLoading }: RecentEventsTableProps) {
  return (
    <div className={styles.card}>
      <div className={styles.header}>
        <h3 className={styles.title}>Recent Security Events</h3>
        <Link to="/history" className={styles.viewAll} aria-label="View all security events">
          View All <ArrowRight size={14} aria-hidden="true" />
        </Link>
      </div>

      {isLoading && <LoadingState message="Loading recent events…" />}

      {!isLoading && events.length === 0 && (
        <EmptyState
          title="No security events available."
          description="Events will appear here once the backend starts sending data."
        />
      )}

      {!isLoading && events.length > 0 && (
        <div className={styles.tableWrapper} role="region" aria-label="Recent security events">
          <table className={styles.table}>
            <thead>
              <tr>
                <th scope="col" className={styles.th}>Time</th>
                <th scope="col" className={styles.th}>Source</th>
                <th scope="col" className={styles.th}>Destination</th>
                <th scope="col" className={styles.th}>Score</th>
                <th scope="col" className={styles.th}>Severity</th>
                <th scope="col" className={styles.th}>Attack Type</th>
                <th scope="col" className={styles.th}>Mode</th>
                <th scope="col" className={styles.th}>State</th>
                <th scope="col" className={styles.th}>Action</th>
              </tr>
            </thead>
            <tbody>
              {events.map((event) => (
                <tr key={event.id} className={styles.tr}>
                  <td className={styles.td}>
                    <span className={styles.mono}>{formatTimestamp(event.timestamp)}</span>
                  </td>
                  <td className={styles.td}>
                    <span className={styles.mono}>
                      {event.sourceIp}:{event.sourcePort}
                    </span>
                  </td>
                  <td className={styles.td}>
                    <span className={styles.mono}>
                      {event.destinationIp}:{event.destinationPort}
                    </span>
                  </td>
                  <td className={styles.td}>
                    <span className={styles.mono}>{formatScore(event.anomalyScore)}</span>
                  </td>
                  <td className={styles.td}>
                    <SeverityBadge severity={event.severity} />
                  </td>
                  <td className={styles.td}>
                    {event.attackType ?? (
                      <span className={styles.normal}>Normal</span>
                    )}
                  </td>
                  <td className={styles.td}>
                    <ModeBadge mode={event.mode} />
                  </td>
                  <td className={styles.td}>
                    <StatusBadge
                      status={event.state as 'active' | 'investigating' | 'resolved' | 'false_positive'}
                    />
                  </td>
                  <td className={styles.td}>
                    <span className={styles.action}>{event.actionTaken}</span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
