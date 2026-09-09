/**
 * SecureNet — ReportsTable
 *
 * Paginated table of generated reports.
 * Download triggers a navigation to the backend download URL.
 * Delete uses ConfirmDialog.
 * No fake reports, no fake download links.
 */

import { useState } from 'react';
import { Download, Trash2, FileText } from 'lucide-react';
import type { Report } from '../../types/reports.types';
import { ConfirmDialog } from '../common/ConfirmDialog';
import { EmptyState } from '../common/EmptyState';
import { LoadingState } from '../common/LoadingState';
import { ErrorState } from '../common/ErrorState';
import { formatTimestamp, formatDate, formatBytes } from '../../utils/format';
import styles from './ReportsTable.module.css';

const STATUS_LABEL: Record<string, string> = {
  pending:    'Pending',
  generating: 'Generating',
  ready:      'Ready',
  failed:     'Failed',
};

const STATUS_CLASS: Record<string, string> = {
  pending:    'statusPending',
  generating: 'statusGenerating',
  ready:      'statusReady',
  failed:     'statusFailed',
};

const FORMAT_LABEL: Record<string, string> = {
  pdf:  'PDF',
  csv:  'CSV',
  json: 'JSON',
};

interface ReportsTableProps {
  reports: Report[];
  isLoading: boolean;
  isError: boolean;
  onDelete: (report: Report) => void;
  isDeleting: boolean;
  onRetry: () => void;
}

export function ReportsTable({
  reports,
  isLoading,
  isError,
  onDelete,
  isDeleting,
  onRetry,
}: ReportsTableProps) {
  const [deleteTarget, setDeleteTarget] = useState<Report | null>(null);

  function handleDownload(report: Report) {
    if (!report.downloadUrl) return;
    window.open(report.downloadUrl, '_blank', 'noopener,noreferrer');
  }

  function confirmDelete(report: Report) {
    setDeleteTarget(report);
  }

  function executeDelete() {
    if (!deleteTarget) return;
    onDelete(deleteTarget);
    setDeleteTarget(null);
  }

  if (isLoading) return <LoadingState message="Loading reports…" />;

  if (isError) {
    return (
      <ErrorState
        title="Reports unavailable"
        message="Reports could not be loaded. The backend API is not yet connected."
        onRetry={onRetry}
      />
    );
  }

  if (reports.length === 0) {
    return (
      <EmptyState
        icon={<FileText size={32} />}
        title="No reports yet"
        description="Generate your first report using the button above."
      />
    );
  }

  return (
    <>
      <div className={styles.tableWrapper}>
        <table className={styles.table}>
          <thead>
            <tr>
              <th className={styles.th}>Name</th>
              <th className={styles.th}>Date Range</th>
              <th className={styles.th}>Format</th>
              <th className={styles.th}>Status</th>
              <th className={styles.th}>Size</th>
              <th className={styles.th}>Generated</th>
              <th className={styles.th} aria-label="Actions" />
            </tr>
          </thead>
          <tbody>
            {reports.map((report) => (
              <tr key={report.id} className={styles.tr}>
                <td className={styles.td}>
                  <span className={styles.reportName}>{report.name}</span>
                  {report.description && (
                    <span className={styles.reportDesc}>{report.description}</span>
                  )}
                </td>
                <td className={styles.tdMono}>
                  {formatDate(report.dateRangeStart)} — {formatDate(report.dateRangeEnd)}
                </td>
                <td className={styles.td}>
                  <span className={styles.formatBadge}>
                    {FORMAT_LABEL[report.format] ?? report.format.toUpperCase()}
                  </span>
                </td>
                <td className={styles.td}>
                  <span
                    className={`${styles.statusBadge} ${
                      styles[STATUS_CLASS[report.status] ?? '']
                    }`}
                  >
                    {STATUS_LABEL[report.status] ?? report.status}
                  </span>
                </td>
                <td className={styles.tdMono}>
                  {report.sizeBytes !== null ? formatBytes(report.sizeBytes) : '—'}
                </td>
                <td className={styles.tdMono}>{formatTimestamp(report.generatedAt)}</td>
                <td className={styles.tdActions}>
                  <button
                    className={styles.actionBtn}
                    onClick={() => handleDownload(report)}
                    disabled={report.status !== 'ready' || !report.downloadUrl}
                    aria-label={`Download ${report.name}`}
                    title={report.status !== 'ready' ? 'Report not ready' : !report.downloadUrl ? 'Download not available' : 'Download'}
                  >
                    <Download size={14} />
                  </button>
                  <button
                    className={`${styles.actionBtn} ${styles.deleteActionBtn}`}
                    onClick={() => confirmDelete(report)}
                    aria-label={`Delete ${report.name}`}
                  >
                    <Trash2 size={14} />
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <ConfirmDialog
        isOpen={deleteTarget !== null}
        title="Delete Report"
        description={
          deleteTarget
            ? `Permanently delete "${deleteTarget.name}"? This cannot be undone.`
            : ''
        }
        confirmLabel="Delete"
        variant="danger"
        isLoading={isDeleting}
        onConfirm={executeDelete}
        onCancel={() => setDeleteTarget(null)}
      />
    </>
  );
}
