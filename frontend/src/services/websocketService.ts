/**
 * SecureNet — WebSocket Service
 *
 * Manages a single persistent WebSocket connection to the backend
 * live monitoring feed.
 *
 * Features:
 *  - Automatic reconnection with exponential back-off
 *  - Typed message dispatching via event listeners
 *  - Connection status tracking
 *
 * Usage:
 *   wsService.connect();
 *   wsService.on('live_score', handler);
 *   wsService.disconnect();
 *
 * The access token is sent as ?token=… (browsers cannot set headers on
 * WebSockets). If VITE_WS_URL is not set the URL is derived from the page.
 */

import type {
  WebSocketMessage,
  WebSocketMessageType,
  WebSocketStatus,
} from '../types/websocket.types';
import { tokenStore } from './apiClient';

// ── Config ────────────────────────────────────────────────────────────────────

const WS_URL: string =
  import.meta.env.VITE_WS_URL ||
  `${window.location.protocol === 'https:' ? 'wss' : 'ws'}://${window.location.host}/ws/live`;
const WS_POLICY_VIOLATION = 1008; // server rejected the token
const RECONNECT_BASE_DELAY_MS = 1000;
const RECONNECT_MAX_DELAY_MS = 30000;
const RECONNECT_MAX_ATTEMPTS = 10;
const PING_INTERVAL_MS = 30000;

// ── Listener Map ──────────────────────────────────────────────────────────────

type MessageHandler<T = unknown> = (message: WebSocketMessage<T>) => void;
type StatusHandler = (status: WebSocketStatus) => void;

// ── Service ───────────────────────────────────────────────────────────────────

class WebSocketService {
  private socket: WebSocket | null = null;
  private status: WebSocketStatus = 'idle';
  private reconnectAttempts = 0;
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private pingTimer: ReturnType<typeof setInterval> | null = null;

  private readonly messageListeners = new Map<
    WebSocketMessageType,
    Set<MessageHandler>
  >();
  private readonly statusListeners = new Set<StatusHandler>();

  // ── Public API ──────────────────────────────────────────────────────────────

  connect(): void {
    const token = tokenStore.getAccess();
    if (!token) {
      this.setStatus('disconnected');
      return;
    }

    if (
      this.socket &&
      (this.socket.readyState === WebSocket.OPEN ||
        this.socket.readyState === WebSocket.CONNECTING)
    ) {
      return;
    }

    this.setStatus('connecting');

    try {
      const url = `${WS_URL}${WS_URL.includes('?') ? '&' : '?'}token=${encodeURIComponent(token)}`;
      this.socket = new WebSocket(url);
      this.attachSocketHandlers();
    } catch (err) {
      console.error('[SecureNet WS] Failed to create WebSocket:', err);
      this.setStatus('error');
    }
  }

  /** Force a fresh connection (e.g. after the access token changed). */
  reconnect(): void {
    this.disconnect();
    this.connect();
  }

  disconnect(): void {
    this.clearTimers();
    this.reconnectAttempts = 0;
    if (this.socket) {
      this.socket.onclose = null; // prevent reconnect on intentional close
      this.socket.close();
      this.socket = null;
    }
    this.setStatus('disconnected');
  }

  /** Subscribe to a specific message type */
  on<T = unknown>(
    type: WebSocketMessageType,
    handler: MessageHandler<T>
  ): () => void {
    if (!this.messageListeners.has(type)) {
      this.messageListeners.set(type, new Set());
    }
    this.messageListeners.get(type)!.add(handler as MessageHandler);

    // Return unsubscribe function
    return () => {
      this.messageListeners.get(type)?.delete(handler as MessageHandler);
    };
  }

  /** Subscribe to connection status changes */
  onStatusChange(handler: StatusHandler): () => void {
    this.statusListeners.add(handler);
    handler(this.status); // emit current status immediately
    return () => {
      this.statusListeners.delete(handler);
    };
  }

  getStatus(): WebSocketStatus {
    return this.status;
  }

  // ── Private ──────────────────────────────────────────────────────────────────

  private attachSocketHandlers(): void {
    if (!this.socket) return;

    this.socket.onopen = () => {
      this.reconnectAttempts = 0;
      this.setStatus('connected');
      this.startPing();
    };

    this.socket.onmessage = (event: MessageEvent<string>) => {
      try {
        const message = JSON.parse(event.data) as WebSocketMessage;
        this.dispatch(message);
      } catch (err) {
        console.warn('[SecureNet WS] Failed to parse message:', err);
      }
    };

    this.socket.onerror = () => {
      console.error('[SecureNet WS] WebSocket error');
      this.setStatus('error');
    };

    this.socket.onclose = (event: CloseEvent) => {
      this.clearPing();
      this.socket = null;
      if (event.code === WS_POLICY_VIOLATION) {
        // Token rejected — a fresh token (after refresh/login) is needed
        this.setStatus('error');
        return;
      }
      this.scheduleReconnect();
    };
  }

  private dispatch(message: WebSocketMessage): void {
    const handlers = this.messageListeners.get(message.type);
    if (handlers) {
      handlers.forEach((h) => h(message));
    }
  }

  private setStatus(status: WebSocketStatus): void {
    this.status = status;
    this.statusListeners.forEach((h) => h(status));
  }

  private scheduleReconnect(): void {
    if (this.reconnectTimer !== null) return;
    if (this.reconnectAttempts >= RECONNECT_MAX_ATTEMPTS) {
      console.error('[SecureNet WS] Max reconnect attempts reached.');
      this.setStatus('error');
      return;
    }

    this.setStatus('reconnecting');
    this.reconnectAttempts += 1;

    const delay = Math.min(
      RECONNECT_BASE_DELAY_MS * Math.pow(2, this.reconnectAttempts - 1),
      RECONNECT_MAX_DELAY_MS
    );

    this.reconnectTimer = setTimeout(() => {
      this.reconnectTimer = null;
      this.connect();
    }, delay);
  }

  private startPing(): void {
    this.clearPing();
    this.pingTimer = setInterval(() => {
      if (this.socket?.readyState === WebSocket.OPEN) {
        this.socket.send(JSON.stringify({ type: 'ping' }));
      }
    }, PING_INTERVAL_MS);
  }

  private clearPing(): void {
    if (this.pingTimer !== null) {
      clearInterval(this.pingTimer);
      this.pingTimer = null;
    }
  }

  private clearTimers(): void {
    if (this.reconnectTimer !== null) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
    this.clearPing();
  }
}

// Singleton instance shared across the application
export const wsService = new WebSocketService();
