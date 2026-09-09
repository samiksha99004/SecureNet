/**
 * SecureNet — Reports Page
 *
 * Features:
 *  - Summary cards (total, last 7 days, this month)
 *  - Paginated reports table with download and delete
 *  - Generate Report modal (date range, severity, state, format, breakdown)
 *
 * No fake report records or fake downloads.
 * Download only activates for ready reports with a real downloadUrl.
 * All operations go through reportsService → backend API.
 */

import { useCallback, useState } from 'react';
import { Plus } from 'lucide-react';
import { MainLayout } from '../components/layout/MainLayout';
import { PageHeader } from '../components/common/PageHeader';
import { ReportSummaryCards } from '../components/reports/ReportSummaryCards';
import { ReportsTable } from '../components/reports/ReportsTable';
import { GenerateReportModal } from '../components/reports/GenerateReportModal';
import { useAsyncData } from '../hooks/useAsyncData';
import { useToast } from '../components/common/Toast';
import {
  getReportSummary,
  getReports,
  generateReport,
  deleteReport,
} from '../services/reportsService';
import type { Report, GenerateReportRequest } from '../types/reports.types';
import styles from './ReportsPage.module.css';

export function ReportsPage() {
  const { showToast } = useToast();

  const [generateOpen, setGenerateOpen] = useState(false);
  const [isGenerating, setIsGenerating] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);

  const summaryFetcher = useCallback(() => getReportSummary(), []);
  const reportsFetcher = useCallback(() => getReports({ page: 1, pageSize: 50 }), []);

  const summary = useAsyncData(summaryFetcher);
  const reports = useAsyncData(reportsFetcher);

  async function handleGenerate(req: GenerateReportRequest) {
    setIsGenerating(true);
    try {
      await generateReport(req);
      showToast({ message: 'Report generation started.', variant: 'success' });
      setGenerateOpen(false);
      void reports.refetch();
      void summary.refetch();
    } catch {
      showToast({ message: 'Could not generate report — backend not connected.', variant: 'error' });
    } finally {
      setIsGenerating(false);
    }
  }

  async function handleDelete(report: Report) {
    setIsDeleting(true);
    try {
      await deleteReport(report.id);
      showToast({ message: `"${report.name}" deleted.`, variant: 'success' });
      void reports.refetch();
      void summary.refetch();
    } catch {
      showToast({ message: 'Could not delete report — backend not connected.', variant: 'error' });
    } finally {
      setIsDeleting(false);
    }
  }

  return (
    <MainLayout title="Reports">
      <div className={styles.page}>
        <PageHeader
          title="Security Reports"
          description="Generate, download, and manage security event reports."
          actions={
            <button
              type="button"
              className={styles.generateBtn}
              onClick={() => setGenerateOpen(true)}
            >
              <Plus size={14} aria-hidden="true" />
              Generate Report
            </button>
          }
        />

        {/* Summary */}
        <ReportSummaryCards
          data={summary.data}
          isLoading={summary.isLoading}
        />

        {/* Reports table */}
        <ReportsTable
          reports={reports.data?.data ?? []}
          isLoading={reports.isLoading}
          isError={reports.isError}
          onDelete={handleDelete}
          isDeleting={isDeleting}
          onRetry={reports.refetch}
        />
      </div>

      {/* Generate modal */}
      <GenerateReportModal
        isOpen={generateOpen}
        isGenerating={isGenerating}
        onConfirm={handleGenerate}
        onCancel={() => setGenerateOpen(false)}
      />
    </MainLayout>
  );
}
