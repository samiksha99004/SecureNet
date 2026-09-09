/**
 * SecureNet — WebSocket Types
 *
 * Defines the message protocol for the live monitoring WebSocket feed.
 * The backend will send messages conforming to these shapes.
 */

// ── Connection State ──────────────────────────────────────────────────────────

export type WebSocketStatus =
  | 'idle'
  | 'connecting'
  | 'connected'
  | 'disconnected'
  | 'reconnecting'
  | 'error';

// ── Message Types ─────────────────────────────────────────────────────────────

export type WebSocketMessageType =
  | 'live_score'
  | 'host_status'
  | 'protocol_distribution'
  | 'top_sources'
  | 'alert'
  | 'system_status'
  | 'ping'
  | 'pong';

// ── Base Message ──────────────────────────────────────────────────────────────

export interface WebSocketMessage<T = unknown> {
  type: WebSocketMessageType;
  timestamp: string;  // ISO 8601
  payload: T;
}

// ── Specific Payloads ─────────────────────────────────────────────────────────

export interface LiveScorePayload {
  anomalyScore: number;
  severity: string;
  sourceIp: string;
  destinationIp: string;
  protocol: string;
  attackType: string | null;
}

export interface HostStatusPayload {
  cpuPercent: number;
  memoryPercent: number;
  networkBytesPerSec: number;
  uptime: number;
}

export interface AlertPayload {
  eventId: string;
  severity: string;
  message: string;
  attackType: string | null;
}

export interface SystemStatusPayload {
  detectionEnabled: boolean;
  mode: string;
  modelStatus: string;
  activeFlows: number;
}
