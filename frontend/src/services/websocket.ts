import { GenerationUpdate, LogMessage, ResultsData } from '../types';

export type WSStatus = 'DISCONNECTED' | 'CONNECTING' | 'CONNECTED' | 'RUNNING' | 'ERROR';

export interface WSEventHandlers {
  onStatusChange?: (status: WSStatus, message?: string) => void;
  onLog?: (log: LogMessage) => void;
  onGeneration?: (gen: GenerationUpdate) => void;
  onFinished?: (exitCode: number, success: boolean, message: string, results?: ResultsData) => void;
  onError?: (err: string) => void;
}

export function getWebSocketUrl(): string {
  if (import.meta.env.VITE_WS_URL) {
    return import.meta.env.VITE_WS_URL as string;
  }
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const host = window.location.host;
  return `${protocol}//${host}/ws/run`;
}

export class ExecutionWebSocket {
  private ws: WebSocket | null = null;
  private handlers: WSEventHandlers = {};
  private reconnectTimeout: any = null;
  private url: string;

  constructor(handlers: WSEventHandlers = {}) {
    this.handlers = handlers;
    this.url = getWebSocketUrl();
  }

  public connect(): void {
    if (this.ws && (this.ws.readyState === WebSocket.OPEN || this.ws.readyState === WebSocket.CONNECTING)) {
      return;
    }

    this.handlers.onStatusChange?.('CONNECTING', 'Connecting to execution server...');

    try {
      this.ws = new WebSocket(this.url);

      this.ws.onopen = () => {
        this.handlers.onStatusChange?.('CONNECTED', 'Execution server connected.');
        this.handlers.onLog?.({
          id: Math.random().toString(36).substring(2, 9),
          timestamp: new Date().toLocaleTimeString(),
          stream: 'system',
          text: '[SYSTEM] Connected to DTWEP WebSocket execution engine.',
        });
      };

      this.ws.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data);
          this.handleMessage(msg);
        } catch (e) {
          console.error('Error parsing WS message:', e);
        }
      };

      this.ws.onclose = () => {
        this.handlers.onStatusChange?.('DISCONNECTED', 'Disconnected from execution server.');
        clearTimeout(this.reconnectTimeout);
        this.reconnectTimeout = setTimeout(() => this.connect(), 3000);
      };

      this.ws.onerror = (e) => {
        console.error('WebSocket error:', e);
        this.handlers.onStatusChange?.('ERROR', 'WebSocket error encountered.');
      };
    } catch (err) {
      console.error('Failed to create WebSocket:', err);
      this.handlers.onStatusChange?.('ERROR', 'Failed to connect to execution server.');
    }
  }

  private handleMessage(msg: any): void {
    if (msg.type === 'status') {
      const st = msg.status === 'RUNNING' ? 'RUNNING' : 'CONNECTED';
      this.handlers.onStatusChange?.(st, msg.message);
      if (msg.message) {
        this.handlers.onLog?.({
          id: Math.random().toString(36).substring(2, 9),
          timestamp: new Date().toLocaleTimeString(),
          stream: 'system',
          text: `[STATUS] ${msg.message}`,
        });
      }
    } else if (msg.type === 'log') {
      this.handlers.onLog?.({
        id: Math.random().toString(36).substring(2, 9),
        timestamp: new Date().toLocaleTimeString(),
        stream: msg.stream || 'stdout',
        text: msg.line,
      });
    } else if (msg.type === 'generation') {
      this.handlers.onGeneration?.(msg.data);
      this.handlers.onLog?.({
        id: Math.random().toString(36).substring(2, 9),
        timestamp: new Date().toLocaleTimeString(),
        stream: 'system',
        text: `[GA Gen ${msg.data.generation}] Best Fitness (Loss): ${msg.data.best_fitness.toFixed(4)}`,
      });
    } else if (msg.type === 'finished') {
      this.handlers.onStatusChange?.('CONNECTED', msg.message);
      this.handlers.onFinished?.(msg.exit_code, msg.success, msg.message, msg.results);
      this.handlers.onLog?.({
        id: Math.random().toString(36).substring(2, 9),
        timestamp: new Date().toLocaleTimeString(),
        stream: msg.success ? 'system' : 'stderr',
        text: `[FINISHED] ${msg.message}`,
      });
    } else if (msg.type === 'error') {
      this.handlers.onError?.(msg.message);
      this.handlers.onLog?.({
        id: Math.random().toString(36).substring(2, 9),
        timestamp: new Date().toLocaleTimeString(),
        stream: 'stderr',
        text: `[ERROR] ${msg.message}`,
      });
    }
  }

  public startModule(caseId: string, modId: string, forceModelA: boolean = false): void {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
      this.connect();
      setTimeout(() => this.startModule(caseId, modId, forceModelA), 500);
      return;
    }
    this.handlers.onStatusChange?.('RUNNING', `Starting ${modId}...`);
    this.ws.send(JSON.stringify({
      action: 'start_module',
      case_id: caseId,
      mod_id: modId,
      exp_id: modId,
      force_model_a: forceModelA,
    }));
  }

  public startExperiment(caseId: string, expId: string, forceModelA: boolean = false): void {
    this.startModule(caseId, expId, forceModelA);
  }

  public startCalibration(caseId: string, params: { pop_size: number; generations: number; mutation_rate: number; weights?: Record<string, number> }): void {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
      this.connect();
      setTimeout(() => this.startCalibration(caseId, params), 500);
      return;
    }
    this.handlers.onStatusChange?.('RUNNING', 'Starting Genetic Algorithm calibration...');
    this.ws.send(JSON.stringify({
      action: 'start_calibration',
      case_id: caseId,
      ...params,
    }));
  }

  public stop(): void {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({ action: 'stop' }));
    }
  }

  public disconnect(): void {
    clearTimeout(this.reconnectTimeout);
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }
}
