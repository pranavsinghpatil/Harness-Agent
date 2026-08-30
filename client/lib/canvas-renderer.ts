import { ScenarioDefinition, TelemetryFrame } from "../types/simulation";

export interface CanvasRenderOptions {
  arenaSize?: number; // default 50 meters
  trajectoryTrail?: Array<{ x: number; y: number }>;
}

export function drawEmptyArena(
  ctx: CanvasRenderingContext2D,
  width: number,
  height: number,
  scenario: ScenarioDefinition | null,
  options: CanvasRenderOptions = {}
) {
  const arenaSize = options.arenaSize ?? (scenario?.world?.arena_size?.[0] ?? 50.0);
  const scale = width / arenaSize;

  // Background
  ctx.fillStyle = "#020617";
  ctx.fillRect(0, 0, width, height);

  // Grid lines
  ctx.strokeStyle = "#1e293b";
  ctx.lineWidth = 1;
  const gridSize = 5.0 * scale; // 5m grid

  for (let x = 0; x <= width; x += gridSize) {
    ctx.beginPath();
    ctx.moveTo(x, 0);
    ctx.lineTo(x, height);
    ctx.stroke();
  }

  for (let y = 0; y <= height; y += gridSize) {
    ctx.beginPath();
    ctx.moveTo(0, y);
    ctx.lineTo(width, y);
    ctx.stroke();
  }

  // Draw Goal if scenario specified
  if (scenario?.world?.goal) {
    const [gxRaw, gyRaw] = scenario.world.goal;
    const gx = gxRaw * scale;
    const gy = height - gyRaw * scale;

    // Outer glow ring
    ctx.strokeStyle = "rgba(245, 158, 11, 0.4)";
    ctx.lineWidth = 3;
    ctx.beginPath();
    ctx.arc(gx, gy, 14, 0, 2 * Math.PI);
    ctx.stroke();

    // Inner goal disc
    ctx.fillStyle = "#f59e0b";
    ctx.beginPath();
    ctx.arc(gx, gy, 8, 0, 2 * Math.PI);
    ctx.fill();

    ctx.fillStyle = "#ffffff";
    ctx.font = "bold 10px monospace";
    ctx.fillText("GOAL", gx - 14, gy - 16);
  }

  // Draw Static Obstacles
  if (scenario?.world?.obstacles) {
    scenario.world.obstacles
      .filter((o) => o.type !== "dynamic")
      .forEach((obs) => {
        const ox = obs.x * scale;
        const oy = height - obs.y * scale;
        const ow = (obs.length ?? 1.5) * scale;
        const oh = (obs.width ?? 1.5) * scale;

        ctx.fillStyle = "#475569";
        ctx.fillRect(ox - ow / 2, oy - oh / 2, ow, oh);
        ctx.strokeStyle = "#64748b";
        ctx.lineWidth = 1.5;
        ctx.strokeRect(ox - ow / 2, oy - oh / 2, ow, oh);
      });
  }
}

export function drawTelemetryFrame(
  ctx: CanvasRenderingContext2D,
  width: number,
  height: number,
  frame: TelemetryFrame,
  scenario: ScenarioDefinition | null,
  options: CanvasRenderOptions = {}
) {
  const arenaSize = options.arenaSize ?? (scenario?.world?.arena_size?.[0] ?? 50.0);
  const scale = width / arenaSize;

  // Background
  ctx.fillStyle = "#020617";
  ctx.fillRect(0, 0, width, height);

  // Background grid
  ctx.strokeStyle = "#0f172a";
  ctx.lineWidth = 1;
  const gridSize = 5.0 * scale; // 5 meter grid lines

  for (let x = 0; x <= width; x += gridSize) {
    ctx.beginPath();
    ctx.moveTo(x, 0);
    ctx.lineTo(x, height);
    ctx.stroke();
  }

  for (let y = 0; y <= height; y += gridSize) {
    ctx.beginPath();
    ctx.moveTo(0, y);
    ctx.lineTo(width, y);
    ctx.stroke();
  }

  // Draw Trajectory Trail if provided
  if (options.trajectoryTrail && options.trajectoryTrail.length > 1) {
    ctx.beginPath();
    ctx.strokeStyle = "rgba(99, 102, 241, 0.45)";
    ctx.lineWidth = 2;
    ctx.setLineDash([4, 4]);
    for (let i = 0; i < options.trajectoryTrail.length; i++) {
      const pt = options.trajectoryTrail[i];
      const px = pt.x * scale;
      const py = height - pt.y * scale;
      if (i === 0) {
        ctx.moveTo(px, py);
      } else {
        ctx.lineTo(px, py);
      }
    }
    ctx.stroke();
    ctx.setLineDash([]);
  }

  // Draw Goal
  if (scenario?.world?.goal) {
    const [gxRaw, gyRaw] = scenario.world.goal;
    const gx = gxRaw * scale;
    const gy = height - gyRaw * scale;

    ctx.strokeStyle = "rgba(251, 191, 36, 0.4)";
    ctx.lineWidth = 3;
    ctx.beginPath();
    ctx.arc(gx, gy, 14, 0, 2 * Math.PI);
    ctx.stroke();

    ctx.fillStyle = "#fbbf24";
    ctx.beginPath();
    ctx.arc(gx, gy, 8, 0, 2 * Math.PI);
    ctx.fill();

    ctx.fillStyle = "#ffffff";
    ctx.font = "bold 10px monospace";
    ctx.fillText("GOAL", gx - 14, gy - 16);
  }

  // Draw Static Obstacles
  if (scenario?.world?.obstacles) {
    scenario.world.obstacles
      .filter((o) => o.type !== "dynamic")
      .forEach((obs) => {
        const ox = obs.x * scale;
        const oy = height - obs.y * scale;
        const ow = (obs.length ?? 1.5) * scale;
        const oh = (obs.width ?? 1.5) * scale;

        ctx.fillStyle = "#334155";
        ctx.fillRect(ox - ow / 2, oy - oh / 2, ow, oh);
        ctx.strokeStyle = "#64748b";
        ctx.lineWidth = 1.5;
        ctx.strokeRect(ox - ow / 2, oy - oh / 2, ow, oh);
      });
  }

  // Draw Dynamic Obstacles
  if (frame.dynamic_obstacles && frame.dynamic_obstacles.length > 0) {
    frame.dynamic_obstacles.forEach((dyn) => {
      const dx = dyn.x * scale;
      const dy = height - dyn.y * scale;

      ctx.fillStyle = "#f43f5e";
      ctx.beginPath();
      ctx.arc(dx, dy, 7, 0, 2 * Math.PI);
      ctx.fill();

      ctx.strokeStyle = "#fda4af";
      ctx.lineWidth = 2;
      ctx.stroke();

      ctx.fillStyle = "#fda4af";
      ctx.font = "9px monospace";
      ctx.fillText(dyn.id || dyn.obstacle_id || "obs", dx - 15, dy - 10);
    });
  }

  // Draw Rover
  const vState = frame.vehicle_state || (frame as unknown as { vehicle?: { x: number; y: number; heading: number; velocity: number } })?.vehicle || { x: 0, y: 0, heading: 0, velocity: 0 };
  const rx = (vState.x ?? 0) * scale;
  const ry = height - (vState.y ?? 0) * scale;
  const rHeading = -(vState.heading ?? 0); // Invert Y for canvas coordinate space

  ctx.save();
  ctx.translate(rx, ry);
  ctx.rotate(rHeading);

  // Clearance halo (red if dangerously close < 1.0m, indigo otherwise)
  const isDanger = (frame.min_clearance ?? 2.0) < 1.0;
  ctx.strokeStyle = isDanger ? "rgba(244, 63, 94, 0.6)" : "rgba(99, 102, 241, 0.3)";
  ctx.lineWidth = isDanger ? 2 : 1;
  ctx.beginPath();
  ctx.arc(0, 0, 2.0 * scale, 0, 2 * Math.PI);
  ctx.stroke();

  // Rover body box (1.4m x 0.9m)
  const rLength = 1.4 * scale;
  const rWidth = 0.9 * scale;

  ctx.fillStyle = isDanger ? "#e11d48" : "#6366f1";
  ctx.fillRect(-rLength / 2, -rWidth / 2, rLength, rWidth);
  ctx.strokeStyle = isDanger ? "#ffe4e6" : "#c7d2fe";
  ctx.lineWidth = 2;
  ctx.strokeRect(-rLength / 2, -rWidth / 2, rLength, rWidth);

  // Heading nose pointer vector
  ctx.strokeStyle = "#38bdf8";
  ctx.lineWidth = 3;
  ctx.beginPath();
  ctx.moveTo(0, 0);
  ctx.lineTo(rLength / 2 + 12, 0);
  ctx.stroke();

  ctx.restore();
}

