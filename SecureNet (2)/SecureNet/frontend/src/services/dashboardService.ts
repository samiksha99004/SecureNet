/**
 * SecureNet — Dashboard Service
 *
 * Fetches dashboard summary data, host status, protocol
 * distribution, and top source IPs.
 *
 * TODO (backend): Connect all endpoints once the API is ready.
 */

import { apiClient } from './apiClient';
import type {
  DashboardSummary,
  HostStatus,
  ProtocolDistribution,
  TopSource,
} from '../types/security.types';

/**
 * Fetch the main dashboard summary (KPIs, severity breakdown,
 * attack distribution, recent events).
 * TODO (backend): GET /dashboard/summary
 */
export async function getDashboardSummary(): Promise<DashboardSummary> {
  return apiClient.get<DashboardSummary>('/dashboard/summary');
}

/**
 * Fetch current host resource status.
 * TODO (backend): GET /dashboard/host-status
 */
export async function getHostStatus(): Promise<HostStatus> {
  return apiClient.get<HostStatus>('/dashboard/host-status');
}

/**
 * Fetch current protocol distribution.
 * TODO (backend): GET /dashboard/protocol-distribution
 */
export async function getProtocolDistribution(): Promise<ProtocolDistribution> {
  return apiClient.get<ProtocolDistribution>('/dashboard/protocol-distribution');
}

/**
 * Fetch top source IPs by flow or anomaly count.
 * TODO (backend): GET /dashboard/top-sources
 */
export async function getTopSources(limit = 5): Promise<TopSource[]> {
  return apiClient.get<TopSource[]>(`/dashboard/top-sources?limit=${limit}`);
}
