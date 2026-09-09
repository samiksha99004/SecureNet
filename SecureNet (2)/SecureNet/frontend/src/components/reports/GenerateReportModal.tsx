/**
 * SecureNet — GenerateReportModal
 *
 * Modal form to generate a new security report.
 * Fields: name, description, date range (start/end), format,
 * severity filter, state filter, optional attack breakdown.
 *
 * No fake reports are created — all generation goes through
 * reportsService → backend API.
 */

import { useEffect, useRef, useState } from 'react';
import { X } from 'lucide-react';
import type { GenerateReportRequest, ReportFormat } from '../../types/reports.types';
import styles from './GenerateReportModal.module.css';

interface GenerateReportModalProps {
  isOpen: boolean;
  isGenerating: boolean;
  onConfirm: (req: GenerateReportRequest) => void;
  onCancel: () => void;
}

const FORMAT_OPTIONS: { value: ReportFormat; label: string }[] = [
  { value: 'pdf',  label: 'PDF Report' },
  { value: 'csv',  label: 'CSV Spreadsheet' },
  { value: 'json', label: 'JSON Data' },
];

const SEVERITY_OPTIONS = [
  { value: 'low',    label: 'Low' },
  { value: 'medium', label: 'Medium' },
  { value: 'high',   label: 'High' },
];

const STATE_OPTIONS = [
  { value: 'active',         label: 'Active' },
  { value: 'investigating',  label: 'Investigating' },
  { value: 'resolved',       label: 'Resolved' },
  { value: 'false_positive', label: 'False Positive' },
];

function todayIso(): string {
  return new Date().toISOString().slice(0, 10);
}

function sevenDaysAgoIso(): string {
  const d = new Date();
  d.setDate(d.getDate() - 7);
  return d.toISOString().slice(0, 10);
}

export function GenerateReportModal({
  isOpen,
  isGenerating,
  onConfirm,
  onCancel,
}: GenerateReportModalProps) {
  const firstRef = useRef<HTMLInputElement>(null);

  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [dateStart, setDateStart] = useState(sevenDaysAgoIso());
  const [dateEnd, setDateEnd] = useState(todayIso());
  const [format, setFormat] = useState<ReportFormat>('pdf');
  const [severities, setSeverities] = useState<string[]>(['low', 'medium', 'high']);
  const [states, setStates] = useState<string[]>(['active', 'investigating', 'resolved', 'false_positive']);
  const [includeBreakdown, setIncludeBreakdown] = useState(false);
  const [errors, setErrors] = useState<Record<string, string>>({});

  useEffect(() => {
    if (isOpen) {
      setName('');
      setDescription('');
      setDateStart(sevenDaysAgoIso());
      setDateEnd(todayIso());
      setFormat('pdf');
      setSeverities(['low', 'medium', 'high']);
      setStates(['active', 'investigating', 'resolved', 'false_positive']);
      setIncludeBreakdown(false);
      setErrors({});
      setTimeout(() => firstRef.current?.focus(), 50);
    }
  }, [isOpen]);

  useEffect(() => {
    if (!isOpen) return;
    function onKey(e: KeyboardEvent) { if (e.key === 'Escape') onCancel(); }
    document.addEventListener('keydown', onKey);
    return () => document.removeEventListener('keydown', onKey);
  }, [isOpen, onCancel]);

  function toggleMulti(
    list: string[],
    setList: (v: string[]) => void,
    value: string
  ) {
    setList(
      list.includes(value) ? list.filter((v) => v !== value) : [...list, value]
    );
  }

  function validate(): boolean {
    const errs: Record<string, string> = {};
    if (!name.trim()) errs.name = 'Report name is required.';
    if (!dateStart) errs.dateStart = 'Start date is required.';
    if (!dateEnd) errs.dateEnd = 'End date is required.';
    if (dateStart && dateEnd && dateStart > dateEnd) {
      errs.dateEnd = 'End date must be on or after start date.';
    }
    if (severities.length === 0) errs.severities = 'Select at least one severity.';
    setErrors(errs);
    return Object.keys(errs).length === 0;
  }

  function handleSubmit() {
    if (!validate()) return;
    onConfirm({
      name: name.trim(),
      description: description.trim() || undefined,
      dateRangeStart: new Date(dateStart).toISOString(),
      dateRangeEnd: new Date(dateEnd + 'T23:59:59').toISOString(),
      format,
      filters: {
        severities,
        states,
        attackTypes: [],
        includeResolved: states.includes('resolved'),
        includeBreakdown,
      },
    });
  }

  if (!isOpen) return null;

  return (
    <div
      className={styles.overlay}
      onClick={(e) => { if (e.target === e.currentTarget) onCancel(); }}
      role="presentation"
    >
      <div
        className={styles.modal}
        role="dialog"
        aria-modal="true"
        aria-labelledby="gen-report-title"
      >
        {/* Header */}
        <div className={styles.header}>
          <h2 id="gen-report-title" className={styles.title}>Generate Report</h2>
          <button className={styles.closeBtn} onClick={onCancel} aria-label="Close">
            <X size={16} />
          </button>
        </div>

        {/* Body */}
        <div className={styles.body}>
          {/* Name */}
          <div className={styles.fieldGroup}>
            <label htmlFor="rep-name" className={styles.label}>Report Name</label>
            <input
              ref={firstRef}
              id="rep-name"
              type="text"
              className={styles.input}
              value={name}
              onChange={(e) => { setName(e.target.value); setErrors((p) => ({ ...p, name: '' })); }}
              placeholder="e.g. Weekly Security Summary"
            />
            {errors.name && <p className={styles.error}>{errors.name}</p>}
          </div>

          {/* Description */}
          <div className={styles.fieldGroup}>
            <label htmlFor="rep-desc" className={styles.label}>
              Description <span className={styles.optional}>(optional)</span>
            </label>
            <input
              id="rep-desc"
              type="text"
              className={styles.input}
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Brief description of this report"
            />
          </div>

          {/* Date range */}
          <div className={styles.dateRow}>
            <div className={styles.fieldGroup}>
              <label htmlFor="rep-start" className={styles.label}>Start Date</label>
              <input
                id="rep-start"
                type="date"
                className={styles.input}
                value={dateStart}
                onChange={(e) => { setDateStart(e.target.value); setErrors((p) => ({ ...p, dateStart: '', dateEnd: '' })); }}
              />
              {errors.dateStart && <p className={styles.error}>{errors.dateStart}</p>}
            </div>
            <div className={styles.fieldGroup}>
              <label htmlFor="rep-end" className={styles.label}>End Date</label>
              <input
                id="rep-end"
                type="date"
                className={styles.input}
                value={dateEnd}
                onChange={(e) => { setDateEnd(e.target.value); setErrors((p) => ({ ...p, dateEnd: '' })); }}
              />
              {errors.dateEnd && <p className={styles.error}>{errors.dateEnd}</p>}
            </div>
          </div>

          {/* Format */}
          <div className={styles.fieldGroup}>
            <label htmlFor="rep-format" className={styles.label}>Format</label>
            <select
              id="rep-format"
              className={styles.select}
              value={format}
              onChange={(e) => setFormat(e.target.value as ReportFormat)}
            >
              {FORMAT_OPTIONS.map((o) => (
                <option key={o.value} value={o.value}>{o.label}</option>
              ))}
            </select>
          </div>

          {/* Severity filter */}
          <div className={styles.fieldGroup}>
            <p className={styles.label}>Include Severities</p>
            <div className={styles.checkRow}>
              {SEVERITY_OPTIONS.map((o) => (
                <label key={o.value} className={styles.checkLabel}>
                  <input
                    type="checkbox"
                    checked={severities.includes(o.value)}
                    onChange={() => toggleMulti(severities, setSeverities, o.value)}
                    className={styles.checkbox}
                  />
                  {o.label}
                </label>
              ))}
            </div>
            {errors.severities && <p className={styles.error}>{errors.severities}</p>}
          </div>

          {/* State filter */}
          <div className={styles.fieldGroup}>
            <p className={styles.label}>Include States</p>
            <div className={styles.checkRow}>
              {STATE_OPTIONS.map((o) => (
                <label key={o.value} className={styles.checkLabel}>
                  <input
                    type="checkbox"
                    checked={states.includes(o.value)}
                    onChange={() => toggleMulti(states, setStates, o.value)}
                    className={styles.checkbox}
                  />
                  {o.label}
                </label>
              ))}
            </div>
          </div>

          {/* Attack breakdown */}
          <label className={styles.checkLabelBlock}>
            <input
              type="checkbox"
              checked={includeBreakdown}
              onChange={(e) => setIncludeBreakdown(e.target.checked)}
              className={styles.checkbox}
            />
            <span>
              <strong>Include attack-type breakdown</strong>
              <span className={styles.checkHint}> — adds a per-attack-type summary section</span>
            </span>
          </label>
        </div>

        {/* Footer */}
        <div className={styles.footer}>
          <button className={styles.cancelBtn} onClick={onCancel} disabled={isGenerating}>
            Cancel
          </button>
          <button
            className={styles.generateBtn}
            onClick={handleSubmit}
            disabled={isGenerating}
            aria-busy={isGenerating}
          >
            {isGenerating ? 'Generating…' : 'Generate Report'}
          </button>
        </div>
      </div>
    </div>
  );
}
