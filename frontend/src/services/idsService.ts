/**
 * SecureNet — IDS Control Service
 *
 * OFF / Detection ("monitor") / Protection ("protect") control and status.
 */

import { apiClient } from './apiClient';

// ── Types ─────────────────────────────────────────────────────────────────────

export type IDSMode = 'monitor' | 'protect';

export interface IDSStatus {
  enabled: boolean;
  mode: IDSMode;
  mlLoaded: boolean;
  /** "none" | "isolation_forest" | "xgboost" | "isolation_forest+xgboost" */
  detector: string;
  /** stage-1 threshold in use right now */
  threshold?: number | null;
  captureActive: boolean;
  captureError: string | null;
  packetsProcessed: number;
  flowsAnalyzed: number;
  activeFlows: number;
  anomaliesDetected: number;
  attacksDetected: number;
  blockedIps: number;
  uptimeSeconds: number;
}

export interface IDSControlRequest {
  enabled: boolean;
  mode?: IDSMode;
}

export const MODE_LABELS: Record<IDSMode, string> = {
  monitor: 'Detection',
  protect: 'Protection',
};

export const DETECTOR_LABELS: Record<string, string> = {
  none: 'No model loaded',
  isolation_forest: 'Isolation Forest',
  xgboost: 'XGBoost',
  'isolation_forest+xgboost': 'Isolation Forest + XGBoost',
};

// ── API Calls ─────────────────────────────────────────────────────────────────

/** GET /api/ids/status */
export async function getIDSStatus(): Promise<IDSStatus> {
  return apiClient.get<IDSStatus>('/ids/status');
}

/** POST /api/ids/control */
export async function controlIDS(request: IDSControlRequest): Promise<IDSStatus> {
  return apiClient.post<IDSStatus>('/ids/control', request);
}

export async function startIDS(mode?: IDSMode): Promise<IDSStatus> {
  return controlIDS({ enabled: true, mode });
}

export async function stopIDS(): Promise<IDSStatus> {
  return controlIDS({ enabled: false });
}

export async function setIDSMode(mode: IDSMode): Promise<IDSStatus> {
  return controlIDS({ enabled: true, mode });
}
