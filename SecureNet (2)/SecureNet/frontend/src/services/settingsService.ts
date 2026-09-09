/**
 * SecureNet — Settings Service
 *
 * Read and update all application settings categories.
 *
 * TODO (backend): Connect all endpoints once the API is ready.
 */

import { apiClient } from './apiClient';
import type {
  AllSettings,
  DetectionSettings,
  ProtectionSettings,
  NotificationSettings,
  SystemSettings,
  WhitelistEntry,
  CreateWhitelistEntryRequest,
} from '../types/settings.types';
import type { MessageResponse } from '../types/api.types';

// ── Read Settings ─────────────────────────────────────────────────────────────

/** TODO (backend): GET /settings */
export async function getAllSettings(): Promise<AllSettings> {
  return apiClient.get<AllSettings>('/settings');
}

/** TODO (backend): GET /settings/detection */
export async function getDetectionSettings(): Promise<DetectionSettings> {
  return apiClient.get<DetectionSettings>('/settings/detection');
}

/** TODO (backend): GET /settings/protection */
export async function getProtectionSettings(): Promise<ProtectionSettings> {
  return apiClient.get<ProtectionSettings>('/settings/protection');
}

/** TODO (backend): GET /settings/notifications */
export async function getNotificationSettings(): Promise<NotificationSettings> {
  return apiClient.get<NotificationSettings>('/settings/notifications');
}

/** TODO (backend): GET /settings/system */
export async function getSystemSettings(): Promise<SystemSettings> {
  return apiClient.get<SystemSettings>('/settings/system');
}

// ── Update Settings ───────────────────────────────────────────────────────────

/** TODO (backend): PUT /settings/detection */
export async function updateDetectionSettings(
  data: Partial<DetectionSettings>
): Promise<DetectionSettings> {
  return apiClient.put<DetectionSettings>('/settings/detection', data);
}

/** TODO (backend): PUT /settings/protection */
export async function updateProtectionSettings(
  data: Partial<ProtectionSettings>
): Promise<ProtectionSettings> {
  return apiClient.put<ProtectionSettings>('/settings/protection', data);
}

/** TODO (backend): PUT /settings/notifications */
export async function updateNotificationSettings(
  data: Partial<NotificationSettings>
): Promise<NotificationSettings> {
  return apiClient.put<NotificationSettings>('/settings/notifications', data);
}

/** TODO (backend): PUT /settings/system */
export async function updateSystemSettings(
  data: Partial<SystemSettings>
): Promise<SystemSettings> {
  return apiClient.put<SystemSettings>('/settings/system', data);
}

// ── Whitelist ─────────────────────────────────────────────────────────────────

/** TODO (backend): GET /settings/whitelist */
export async function getWhitelist(): Promise<WhitelistEntry[]> {
  return apiClient.get<WhitelistEntry[]>('/settings/whitelist');
}

/** TODO (backend): POST /settings/whitelist */
export async function addWhitelistEntry(
  data: CreateWhitelistEntryRequest
): Promise<WhitelistEntry> {
  return apiClient.post<WhitelistEntry>('/settings/whitelist', data);
}

/** TODO (backend): DELETE /settings/whitelist/:id */
export async function removeWhitelistEntry(id: string): Promise<MessageResponse> {
  return apiClient.delete<MessageResponse>(`/settings/whitelist/${id}`);
}
