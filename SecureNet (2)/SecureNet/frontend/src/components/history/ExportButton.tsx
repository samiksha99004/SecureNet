/**
 * SecureNet — ExportButton
 *
 * Triggers CSV or PDF export of filtered security events.
 * When the backend export endpoint is unavailable (no base URL
 * configured), shows an informational message instead of
 * attempting a download.
 *
 * Architecture: export URLs are built by eventsService; this
 * component only handles the UI state.
 */

import { useState } from 'react';
import { Download, FileText, FileSpreadsheet, X } from 'lucide-react';
import { cn } from '../../utils/cn';
import styles from './ExportButton.module.css';

interface ExportButtonProps {
  /** Current filter query string (appended to export URL) */
  queryString: string;
  /** Total events matching current filters */
  totalEvents: number | null;
  disabled?: boolean;
}

type ExportFormat = 'csv' | 'pdf';

/** Returns the base API URL — empty string means backend not configured. */
function getApiBase(): string {
  return import.meta.env.VITE_API_BASE_URL ?? '';
}

function buildExportUrl(format: ExportFormat, queryString: string): string {
  const base = getApiBase();
  const qs = queryString ? `${queryString}&format=${format}` : `format=${format}`;
  return `${base}/events/export?${qs}`;
}

export function ExportButton({ queryString, totalEvents, disabled = false }: ExportButtonProps) {
  const [open, setOpen] = useState(false);
  const [unavailableFormat, setUnavailableFormat] = useState<ExportFormat | null>(null);

  const backendConfigured = getApiBase() !== '';

  function handleExport(format: ExportFormat) {
    if (!backendConfigured) {
      setUnavailableFormat(format);
      setOpen(false);
      return;
    }
    const url = buildExportUrl(format, queryString);
    window.open(url, '_blank', 'noopener,noreferrer');
    setOpen(false);
  }

  return (
    <div className={styles.wrapper}>
      {/* Unavailable notice */}
      {unavailableFormat && (
        <div className={styles.unavailableNotice} role="alert">
          <span>
            Export not available — backend API not yet connected.
          </span>
          <button
            className={styles.dismissBtn}
            onClick={() => setUnavailableFormat(null)}
            aria-label="Dismiss"
          >
            <X size={13} />
          </button>
        </div>
      )}

      {/* Trigger button */}
      <button
        type="button"
        className={cn(styles.trigger, open && styles.triggerOpen)}
        onClick={() => setOpen((p) => !p)}
        disabled={disabled || totalEvents === 0}
        aria-haspopup="menu"
        aria-expanded={open}
        aria-label="Export events"
      >
        <Download size={14} aria-hidden="true" />
        Export
      </button>

      {/* Dropdown menu */}
      {open && (
        <>
          <div className={styles.backdrop} onClick={() => setOpen(false)} aria-hidden="true" />
          <div className={styles.menu} role="menu">
            <p className={styles.menuTitle}>Export format</p>

            <button
              role="menuitem"
              className={styles.menuItem}
              onClick={() => handleExport('csv')}
            >
              <FileSpreadsheet size={14} aria-hidden="true" />
              <span>CSV Spreadsheet</span>
              {!backendConfigured && (
                <span className={styles.unavailableTag}>unavailable</span>
              )}
            </button>

            <button
              role="menuitem"
              className={styles.menuItem}
              onClick={() => handleExport('pdf')}
            >
              <FileText size={14} aria-hidden="true" />
              <span>PDF Report</span>
              {!backendConfigured && (
                <span className={styles.unavailableTag}>unavailable</span>
              )}
            </button>

            {totalEvents !== null && (
              <p className={styles.menuNote}>
                {totalEvents.toLocaleString()} event{totalEvents !== 1 ? 's' : ''} will be exported
              </p>
            )}
          </div>
        </>
      )}
    </div>
  );
}
