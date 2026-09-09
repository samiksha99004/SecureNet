/**
 * SecureNet — Reports Types
 */

export type ReportStatus = 'pending' | 'generating' | 'ready' | 'failed';

export type ReportFormat = 'pdf' | 'csv' | 'json';

export interface Report {
  id: string;
  name: string;
  description: string | null;
  dateRangeStart: string;   // ISO 8601
  dateRangeEnd: string;     // ISO 8601
  generatedAt: string;      // ISO 8601
  status: ReportStatus;
  format: ReportFormat;
  sizeBytes: number | null;
  downloadUrl: string | null;
  filters: ReportFilters;
  createdBy: string;        // User ID
}

export interface ReportFilters {
  severities: string[];
  states: string[];
  attackTypes: string[];
  includeResolved: boolean;
  includeBreakdown: boolean;
}

export interface GenerateReportRequest {
  name: string;
  description?: string;
  dateRangeStart: string;
  dateRangeEnd: string;
  format: ReportFormat;
  filters: ReportFilters;
}

export interface ReportSummary {
  totalReports: number;
  recentReportsCount: number;   // last 7 days
  generatedThisMonth: number;
}
