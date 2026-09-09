/**
 * SecureNet — Settings Types
 *
 * Defines the shape for all configurable settings categories.
 * Backend will expose and persist these values through the API.
 */

// ── Detection Settings ────────────────────────────────────────────────────────

export interface DetectionSettings {
  enabled: boolean;
  sensitivity: 'low' | 'medium' | 'high' | 'custom';
  anomalyThreshold: number;      // 0.0 – 1.0
  minFlowsForAnalysis: number;
  analysisIntervalMs: number;
  stage2Enabled: boolean;        // XGBoost classification toggle
  stage2ConfidenceThreshold: number;
}

// ── Protection Settings ───────────────────────────────────────────────────────

export type ProtectionMode = 'monitor' | 'protect';

export interface ProtectionSettings {
  mode: ProtectionMode;
  autoBlock: boolean;
  autoBlockSeverities: string[];       // e.g. ['high']
  blockDurationSeconds: number;
  maxBlockedIps: number;
  notifyOnBlock: boolean;
}

// ── Notification Settings ─────────────────────────────────────────────────────

export interface NotificationSettings {
  emailEnabled: boolean;
  emailAddress: string | null;
  alertOnHigh: boolean;
  alertOnMedium: boolean;
  alertOnBlock: boolean;
  digestEnabled: boolean;
  digestIntervalHours: number;
}

// ── Whitelist Entry ───────────────────────────────────────────────────────────

export type WhitelistEntryType = 'ip' | 'cidr' | 'port' | 'protocol';

export interface WhitelistEntry {
  id: string;
  type: WhitelistEntryType;
  value: string;
  description: string | null;
  createdAt: string;           // ISO 8601
  createdBy: string | null;    // User ID
  active: boolean;
}

export interface CreateWhitelistEntryRequest {
  type: WhitelistEntryType;
  value: string;
  description?: string;
}

// ── System Settings ───────────────────────────────────────────────────────────

export interface SystemSettings {
  logRetentionDays: number;
  maxStoredEvents: number;
  timezone: string;
  dateFormat: string;
  debugMode: boolean;
}

// ── Combined Settings ─────────────────────────────────────────────────────────

export interface AllSettings {
  detection: DetectionSettings;
  protection: ProtectionSettings;
  notifications: NotificationSettings;
  system: SystemSettings;
}
