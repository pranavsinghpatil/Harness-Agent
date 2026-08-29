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

