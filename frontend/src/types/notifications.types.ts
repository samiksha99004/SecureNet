/**
 * SecureNet — Notification Types
 *
 * One NotificationItem per stored security event. The same shape is returned
 * by GET /api/notifications and pushed live as the WebSocket `alert` payload.
 */

import type { ActionTaken, Protocol, SeverityLevel } from './security.types';

export interface NotificationItem {
  eventId: string;
  timestamp: string;          // ISO 8601 (UTC, "Z")
  severity: SeverityLevel;
  attackType: string | null;  // null = unclassified anomaly
  sourceIp: string;
  sourcePort: number;
  destinationIp: string;
  destinationPort: number;
  protocol: Protocol;
  anomalyScore: number;
  actionTaken: ActionTaken;
  message: string;
}

export type EmailDeliveryStatus = 'enabled' | 'disabled' | 'misconfigured';

export interface NotificationStatus {
  emailDelivery: EmailDeliveryStatus;   // server SMTP configuration
  emailAlertsEnabled: boolean;          // Settings → Notifications → email alerts
  recipientCount: number;
  recipients: string[];                 // only returned to admins
  batchSeconds: number;
  emailsSent: number;
  lastError: string | null;
}
