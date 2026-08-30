import {
  TelemetryFrame,
  RunManifest,
  WSStreamMessage,
} from "../types/simulation";

export interface LiveStreamCallbacks {
  onFrame: (frame: TelemetryFrame, status: string, isFinished: boolean) => void;
  onManifest: (manifest: RunManifest) => void;
  onError: (errorMsg: string) => void;
  onClose: () => void;
}

export class SimulationStreamClient {
  private ws: WebSocket | null = null;
  private isManuallyClosed = false;

  constructor(
    private apiBase: string,
    private scenarioId: string,
    private callbacks: LiveStreamCallbacks
  ) {}

  public connect(): void {
    this.isManuallyClosed = false;

    // Convert http/https to ws/wss
    const wsBase = this.apiBase
      .replace(/^http:\/\//i, "ws://")
      .replace(/^https:\/\//i, "wss://");

    const wsUrl = `${wsBase}/ws/live/${encodeURIComponent(this.scenarioId)}`;

    try {
      this.ws = new WebSocket(wsUrl);

      this.ws.onopen = () => {
        console.log(`[WebSocket] Connected to simulation live stream: ${wsUrl}`);
      };

      this.ws.onmessage = (event) => {
        try {
          const msg: WSStreamMessage = JSON.parse(event.data);
          console.log(msg);
          if ("error" in msg && msg.error) {
            this.callbacks.onError(msg.error);
            return;
          }

          if (msg.type === "error") {
            this.callbacks.onError(msg.message || "Unknown streaming error");
            return;
          }

          if (msg.type === "frame") {
            this.callbacks.onFrame(msg.data, msg.status, msg.is_finished);
            return;
          }

          if (msg.type === "manifest") {
            const manifest: RunManifest = {
              run_id: msg.run_id,
              status: msg.status,
              termination_reason: msg.termination_reason,
              duration: msg.duration,
              steps: msg.steps,
              violations_count: msg.violations_count,
              trace_hash: msg.trace_hash,
            };
            this.callbacks.onManifest(manifest);
            return;
          }
        } catch (parseErr) {
          console.error("[WebSocket] Failed to parse message:", parseErr, event.data);
        }
      };

      this.ws.onerror = (err) => {
        console.error("[WebSocket] Live stream connection error:", err);
        if (!this.isManuallyClosed) {
          this.callbacks.onError("WebSocket connection failed or interrupted.");
        }
      };

      this.ws.onclose = () => {
        console.log("[WebSocket] Connection closed.");
        this.callbacks.onClose();
      };
    } catch (err) {
      console.error("[WebSocket] Failed to initialize connection:", err);
      this.callbacks.onError(
        err instanceof Error ? err.message : "Failed to open WebSocket"
      );
    }
  }

  public disconnect(): void {
    this.isManuallyClosed = true;
    if (this.ws) {
      try {
        this.ws.close();
      } catch {
        // Ignore closing errors
      }
      this.ws = null;
    }
  }

  public isConnected(): boolean {
    return this.ws !== null && this.ws.readyState === WebSocket.OPEN;
  }
}

export interface InvestigationStreamCallbacks {
  onEvent: (event: import("../types/simulation").HarnessEvent) => void;
  onStatusChange?: (status: "CONNECTING" | "OPEN" | "CLOSED" | "ERROR") => void;
  onError?: (errorMsg: string) => void;
  onClose?: () => void;
}

export class InvestigationStreamClient {
  private ws: WebSocket | null = null;
  private isManuallyClosed = false;
  private reconnectTimer: NodeJS.Timeout | null = null;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;

  constructor(
    private apiBase: string,
    private investigationId: string,
    private callbacks: InvestigationStreamCallbacks
  ) {}

  public connect(): void {
    this.isManuallyClosed = false;
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }

    const wsBase = this.apiBase
      .replace(/^http:\/\//i, "ws://")
      .replace(/^https:\/\//i, "wss://");

    const wsUrl = `${wsBase}/ws/investigations/${encodeURIComponent(this.investigationId)}`;
    this.callbacks.onStatusChange?.("CONNECTING");

    try {
      this.ws = new WebSocket(wsUrl);

      this.ws.onopen = () => {
        console.log(`[InvestigationWS] Connected to investigation stream: ${wsUrl}`);
        this.reconnectAttempts = 0;
        this.callbacks.onStatusChange?.("OPEN");
      };

      this.ws.onmessage = (event) => {
        try {
          const raw = JSON.parse(event.data);
          if (raw.error) {
            this.callbacks.onError?.(raw.error);
            return;
          }
          // The payload is a serialized HarnessEvent
          this.callbacks.onEvent(raw as import("../types/simulation").HarnessEvent);
        } catch (err) {
          console.error("[InvestigationWS] Failed to parse event JSON:", err, event.data);
        }
      };

      this.ws.onerror = (err) => {
        console.error("[InvestigationWS] Socket error:", err);
        this.callbacks.onStatusChange?.("ERROR");
        if (!this.isManuallyClosed) {
          this.callbacks.onError?.("Investigation stream encountered an error");
        }
      };

      this.ws.onclose = (ev) => {
        console.log(`[InvestigationWS] Stream closed (code: ${ev.code}, reason: ${ev.reason})`);
        this.callbacks.onStatusChange?.("CLOSED");
        this.callbacks.onClose?.();

        // If not manually closed and not a normal terminal close (or 4404), attempt reconnect
        if (!this.isManuallyClosed && ev.code !== 1000 && ev.code !== 4404 && this.reconnectAttempts < this.maxReconnectAttempts) {
          this.reconnectAttempts++;
          const backoff = Math.min(1000 * Math.pow(1.5, this.reconnectAttempts), 5000);
          console.log(`[InvestigationWS] Reconnecting in ${backoff}ms (attempt ${this.reconnectAttempts}/${this.maxReconnectAttempts})...`);
          this.reconnectTimer = setTimeout(() => this.connect(), backoff);
        }
      };
    } catch (err) {
      console.error("[InvestigationWS] Failed to initialize WebSocket:", err);
      this.callbacks.onStatusChange?.("ERROR");
      this.callbacks.onError?.(
        err instanceof Error ? err.message : "Failed to open Investigation WebSocket"
      );
    }
  }

  public disconnect(): void {
    this.isManuallyClosed = true;
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
    if (this.ws) {
      try {
        this.ws.close();
      } catch {
        // Ignore closing errors
      }
      this.ws = null;
    }
    this.callbacks.onStatusChange?.("CLOSED");
  }

  public isConnected(): boolean {
    return this.ws !== null && this.ws.readyState === WebSocket.OPEN;
  }
}


