/**
 * SecureNet — Live Monitoring Hook
 *
 * Manages the WebSocket connection and accumulates live chart data.
 * Components call this hook to access real-time anomaly scores.
 *
 * Returns an empty state with the correct connection status until
 * the backend WebSocket is connected.
 */

import { useCallback, useEffect, useRef, useState } from 'react';
import { wsService } from '../services/websocketService';
import type { WebSocketStatus } from '../types/websocket.types';
import type { LiveChartPoint } from '../types/security.types';
import type { LiveScorePayload, WebSocketMessage } from '../types/websocket.types';

const MAX_CHART_POINTS = 60; // Keep last 60 data points

interface LiveMonitoringState {
  status: WebSocketStatus;
  chartData: LiveChartPoint[];
  lastScore: number | null;
  lastSeverity: string | null;
}

export function useLiveMonitoring() {
  const [state, setState] = useState<LiveMonitoringState>({
    status: 'idle',
    chartData: [],
    lastScore: null,
    lastSeverity: null,
  });

  const stateRef = useRef(state);
  stateRef.current = state;

  useEffect(() => {
    // Subscribe to connection status
    const unsubStatus = wsService.onStatusChange((status) => {
      setState((prev) => ({ ...prev, status }));
    });

    // Subscribe to live score messages
    const unsubScore = wsService.on<LiveScorePayload>(
      'live_score',
      (message: WebSocketMessage<LiveScorePayload>) => {
        const { anomalyScore, severity } = message.payload;
        const time = new Date(message.timestamp).toLocaleTimeString('en-GB');

        setState((prev) => {
          const newPoint: LiveChartPoint = {
            time,
            score: anomalyScore,
            severity: severity as LiveChartPoint['severity'],
          };
          const chartData = [...prev.chartData, newPoint].slice(-MAX_CHART_POINTS);
          return {
            ...prev,
            chartData,
            lastScore: anomalyScore,
            lastSeverity: severity,
          };
        });
      }
    );

    // Connect
    wsService.connect();

    return () => {
      unsubStatus();
      unsubScore();
    };
  }, []);

  const disconnect = useCallback(() => {
    wsService.disconnect();
  }, []);

  const reconnect = useCallback(() => {
    wsService.connect();
  }, []);

  return {
    ...state,
    disconnect,
    reconnect,
    isConnected: state.status === 'connected',
    isConnecting:
      state.status === 'connecting' || state.status === 'reconnecting',
  };
}
