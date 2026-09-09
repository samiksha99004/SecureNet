/**
 * SecureNet — Security Events Service
 *
 * CRUD + query operations for security event history.
 *
 * TODO (backend): Connect all endpoints once the API is ready.
 */

import { apiClient } from './apiClient';
import type { SecurityEvent } from '../types/security.types';
import type {
  PaginatedResponse,
  EventFilterParams,
  MessageResponse,
} from '../types/api.types';

/**
 * Fetch a paginated, filtered list of security events.
 * TODO (backend): GET /events
 */
export async function getEvents(
  params: Partial<EventFilterParams>
): Promise<PaginatedResponse<SecurityEvent>> {
  const qs = buildQueryString(params);
  return apiClient.get<PaginatedResponse<SecurityEvent>>(`/events?${qs}`);
}

/**
 * Fetch a single security event by ID.
 * TODO (backend): GET /events/:id
 */
export async function getEventById(id: string): Promise<SecurityEvent> {
  return apiClient.get<SecurityEvent>(`/events/${id}`);
}

/**
 * Mark an event as resolved.
 * TODO (backend): POST /events/:id/resolve
 */
export async function resolveEvent(id: string): Promise<MessageResponse> {
  return apiClient.post<MessageResponse>(`/events/${id}/resolve`, {});
}

/**
 * Mark an event as a false positive.
 * TODO (backend): POST /events/:id/false-positive
 */
export async function markFalsePositive(id: string): Promise<MessageResponse> {
  return apiClient.post<MessageResponse>(`/events/${id}/false-positive`, {});
}

// ── Helpers ───────────────────────────────────────────────────────────────────

function buildQueryString(params: Partial<EventFilterParams>): string {
  const entries = Object.entries(params).filter(
    ([, v]) => v !== null && v !== undefined && v !== ''
  );
  return new URLSearchParams(
    entries.map(([k, v]) => [k, String(v)])
  ).toString();
}
