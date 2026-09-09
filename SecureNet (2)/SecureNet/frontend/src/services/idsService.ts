/**
 * SecureNet — IDS Control Service
 *
 * Manages IDS enable/disable and status monitoring.
 */

import { apiClient } from './apiClient';

// ── Types ─────────────────────────────────────────────────────────────────────

export interface IDSStatus {
  enabled: boolean;
  mode: 'monitor' | 'protect';
  mlLoaded: boolean;
  packetsProcessed: number;
  flowsAnalyzed: number;
  anomaliesDetected: number;
  attacksDetected: number;
}

export interface IDSControlRequest {
  enabled: boolean;
  mode?: 'monitor' | 'protect';
}

// ── API Calls ─────────────────────────────────────────────────────────────────

/**
 * Get current IDS status
 * GET /api/ids/status
 */
export async function getIDSStatus(): Promise<IDSStatus> {
  return apiClient.get<IDSStatus>('/ids/status');
}

/**
 * Control IDS (start/stop)
 * POST /api/ids/control
 */
export async function controlIDS(request: IDSControlRequest): Promise<IDSStatus> {
  return apiClient.post<IDSStatus>('/ids/control', request);
}

/**
 * Start IDS (automatically enables detection and protection)
 */
export async function startIDS(): Promise<IDSStatus> {
  // Always use protect mode internally - user only sees ON/OFF
  return controlIDS({ enabled: true, mode: 'protect' });
}

/**
 * Stop IDS
 */
export async function stopIDS(): Promise<IDSStatus> {
  return controlIDS({ enabled: false });
}
