/**
 * SecureNet — Reports Service
 *
 * Generate, list, and download security reports.
 *
 * TODO (backend): Connect all endpoints once the API is ready.
 */

import { apiClient } from './apiClient';
import type { Report, GenerateReportRequest, ReportSummary } from '../types/reports.types';
import type { PaginatedResponse, PaginationParams, MessageResponse } from '../types/api.types';

/** TODO (backend): GET /reports/summary */
export async function getReportSummary(): Promise<ReportSummary> {
  return apiClient.get<ReportSummary>('/reports/summary');
}

/** TODO (backend): GET /reports */
export async function getReports(
  params: Partial<PaginationParams>
): Promise<PaginatedResponse<Report>> {
  const qs = new URLSearchParams(
    Object.entries(params)
      .filter(([, v]) => v !== undefined)
      .map(([k, v]) => [k, String(v)])
  ).toString();
  return apiClient.get<PaginatedResponse<Report>>(`/reports?${qs}`);
}

/** TODO (backend): POST /reports */
export async function generateReport(
  request: GenerateReportRequest
): Promise<Report> {
  return apiClient.post<Report>('/reports', request);
}

/** TODO (backend): DELETE /reports/:id */
export async function deleteReport(id: string): Promise<MessageResponse> {
  return apiClient.delete<MessageResponse>(`/reports/${id}`);
}

/**
 * Get a download URL for a report.
 * TODO (backend): GET /reports/:id/download
 * Returns a pre-signed or direct URL to the report file.
 */
export function getReportDownloadUrl(id: string): string {
  const base = import.meta.env.VITE_API_BASE_URL ?? '';
  return `${base}/reports/${id}/download`;
}
