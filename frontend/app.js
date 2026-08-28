/**
 * Harness-Agent Visualizer Client
 * Connects to FastAPI simulation backend, renders 2D canvas, and controls playback.
 */

const API_BASE = window.location.origin.includes(":8000") ? window.location.origin : "http://localhost:8000";

let scenarios = [];
let currentScenario = null;
let currentRunFrames = [];
let currentManifest = null;
let currentFrameIdx = 0;
let isPlaying = false;
let animationTimer = null;

// DOM Elements
const scenarioSelect = document.getElementById("scenario-select");
const scenarioDesc = document.getElementById("scenario-desc");
const seedInput = document.getElementById("seed-input");
const simTimeInput = document.getElementById("sim-time-input");
const btnRun = document.getElementById("btn-run");
const btnReplay = document.getElementById("btn-replay");
const btnPlayPause = document.getElementById("btn-play-pause");
const timelineScrubber = document.getElementById("timeline-scrubber");
const scrubberTime = document.getElementById("scrubber-time");
const faultList = document.getElementById("fault-list");
const canvas = document.getElementById("sim-canvas");
const ctx = canvas.getContext("2d");

// Metrics DOM
const simStatus = document.getElementById("sim-status");
const simTimeDisplay = document.getElementById("sim-time-display");
const simStepDisplay = document.getElementById("sim-step-display");
const statVel = document.getElementById("stat-vel");
const statClearance = document.getElementById("stat-clearance");
const statCmd = document.getElementById("stat-cmd");
const statHeading = document.getElementById("stat-heading");
const hwCpu = document.getElementById("hw-cpu");
const hwCpuBar = document.getElementById("hw-cpu-bar");
const hwTemp = document.getElementById("hw-temp");
const hwThrottled = document.getElementById("hw-throttled");
const hwMisses = document.getElementById("hw-misses");
const hwQueues = document.getElementById("hw-queues");
const manifestRunId = document.getElementById("manifest-run-id");
const manifestHash = document.getElementById("manifest-hash");
const manifestViolations = document.getElementById("manifest-violations");
const safetyBanner = document.getElementById("safety-banner");
const violationText = document.getElementById("violation-text");

// Initialize
async function init() {
  await fetchScenarios();
  setupEventListeners();
  drawEmptyArena();
}

async function fetchScenarios() {
  try {
    const res = await fetch(`${API_BASE}/api/scenarios/`);
    scenarios = await res.json();
    populateScenarioDropdown();
  } catch (err) {
    console.error("Failed to load scenarios:", err);
    scenarioDesc.innerText = "Error connecting to backend API at " + API_BASE;
  }
}

function populateScenarioDropdown() {
  scenarioSelect.innerHTML = "";
  scenarios.forEach((sc) => {
    const opt = document.createElement("option");
    opt.value = sc.id;
    opt.textContent = `${sc.name || sc.id}`;
    scenarioSelect.appendChild(opt);
  });

  if (scenarios.length > 0) {
    onScenarioChange();
  }
}

function onScenarioChange() {
  const scId = scenarioSelect.value;
  currentScenario = scenarios.find((s) => s.id === scId);
  if (!currentScenario) return;

  scenarioDesc.innerText = currentScenario.description || "No description provided.";
  seedInput.value = currentScenario.seed || 42;
  simTimeInput.value = currentScenario.max_sim_time || 15;

  // Render scheduled faults
  faultList.innerHTML = "";
  if (currentScenario.fault_schedule && currentScenario.fault_schedule.length > 0) {
    currentScenario.fault_schedule.forEach((f) => {
      const el = document.createElement("div");
      el.className = "p-2 rounded bg-slate-950 border border-slate-800 text-slate-300";
      el.innerHTML = `
        <div class="flex justify-between items-center font-mono text-[11px] mb-1">
          <span class="text-amber-400 font-semibold">${f.id}</span>
          <span class="text-slate-400">${f.start_time}s - ${(f.start_time + f.duration).toFixed(1)}s</span>
        </div>
        <div class="text-[10px] text-slate-400">Target: <code class="text-indigo-300">${f.target}</code> (${f.type})</div>
      `;
      faultList.appendChild(el);
    });
  } else {
    faultList.innerHTML = '<div class="text-slate-500 italic">No perturbations scheduled (Safe Baseline)</div>';
  }

  drawEmptyArena();
}

function setupEventListeners() {
  scenarioSelect.addEventListener("change", onScenarioChange);

  btnRun.addEventListener("click", async () => {
    await runSelectedScenario();
  });

  btnReplay.addEventListener("click", async () => {
    await replayCurrentRun();
  });

  btnPlayPause.addEventListener("click", () => {
    if (isPlaying) {
      pausePlayback();
    } else {
      startPlayback();
    }
  });

  timelineScrubber.addEventListener("input", (e) => {
    pausePlayback();
    const idx = parseInt(e.target.value, 10);
    renderFrameAtIndex(idx);
  });
}

async function runSelectedScenario() {
  if (!currentScenario) return;
  btnRun.disabled = true;
  btnRun.innerText = "Running Simulation...";
  simStatus.innerText = "SIMULATING...";
  simStatus.className = "text-amber-400 font-semibold uppercase";

  try {
    const payload = {
      scenario_id: currentScenario.id,
      seed: parseInt(seedInput.value, 10),
      max_sim_time: parseFloat(simTimeInput.value),
    };

    const res = await fetch(`${API_BASE}/api/scenarios/run`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    const data = await res.json();
    currentManifest = data.manifest;
    currentRunFrames = data.frames;

    // Update manifest UI
    manifestRunId.innerText = currentManifest.run_id;
    manifestHash.innerText = currentManifest.trace_hash;
    manifestViolations.innerText = currentManifest.violations_count;
    simStatus.innerText = currentManifest.status;
    simStatus.className = currentManifest.status.includes("violation")
      ? "text-rose-400 font-semibold uppercase"
      : "text-emerald-400 font-semibold uppercase";

    btnReplay.disabled = false;
    timelineScrubber.max = currentRunFrames.length - 1;
    timelineScrubber.value = 0;

    startPlayback();
  } catch (err) {
    console.error("Simulation run failed:", err);
    alert("Simulation failed: " + err.message);
  } finally {
    btnRun.disabled = false;
    btnRun.innerText = "Execute Episode";
  }
}

async function replayCurrentRun() {
  if (!currentManifest) return;
  btnReplay.disabled = true;
  btnReplay.innerText = "Verifying Replay...";

  try {
    const res = await fetch(`${API_BASE}/api/scenarios/replay/${currentManifest.run_id}`, {
      method: "POST",
    });
    const data = await res.json();

    if (data.is_bit_exact_match) {
      alert(`✅ Replay Verified! 100% Bit-Exact Determinism match.\nTrace Hash: ${data.original_trace_hash.substring(0, 16)}...`);
    } else {
      alert(`⚠️ Determinism Mismatch: ${data.difference_details}`);
    }
  } catch (err) {
    alert("Replay failed: " + err.message);
  } finally {
    btnReplay.disabled = false;
    btnReplay.innerText = "Deterministic Replay";
  }
}

function startPlayback() {
  if (currentRunFrames.length === 0) return;
  isPlaying = true;
  document.getElementById("play-icon").innerHTML = '<path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zM7 8a1 1 0 012 0v4a1 1 0 11-2 0V8zm5-1a1 1 0 00-1 1v4a1 1 0 102 0V8a1 1 0 00-1-1z" clip-rule="evenodd"/>';

  if (currentFrameIdx >= currentRunFrames.length - 1) {
    currentFrameIdx = 0;
  }

  clearInterval(animationTimer);
  animationTimer = setInterval(() => {
    if (currentFrameIdx >= currentRunFrames.length) {
      pausePlayback();
      return;
    }
    renderFrameAtIndex(currentFrameIdx);
    timelineScrubber.value = currentFrameIdx;
    currentFrameIdx += 1;
  }, 20); // 50 Hz visual update
}

function pausePlayback() {
  isPlaying = false;
  clearInterval(animationTimer);
  document.getElementById("play-icon").innerHTML = '<path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM9.555 7.168A1 1 0 008 8v4a1 1 0 001.555.832l3-2a1 1 0 000-1.664l-3-2z" clip-rule="evenodd"/>';
}

function renderFrameAtIndex(idx) {
  if (idx < 0 || idx >= currentRunFrames.length) return;
  currentFrameIdx = idx;
  const frame = currentRunFrames[idx];

  // Update telemetry stats
  simTimeDisplay.innerText = `${frame.sim_time.toFixed(2)}s`;
  simStepDisplay.innerText = frame.step;
  scrubberTime.innerText = `${frame.sim_time.toFixed(2)}s`;

  statVel.innerText = `${frame.vehicle_state.velocity.toFixed(2)} m/s`;
  statClearance.innerText = frame.min_clearance < 100 ? `${frame.min_clearance.toFixed(2)} m` : "-- m";
  statHeading.innerText = `${((frame.vehicle_state.heading * 180) / Math.PI).toFixed(1)}°`;
  const th = Math.round((frame.actuator_command.throttle || 0) * 100);
  const br = Math.round((frame.actuator_command.brake || 0) * 100);
  statCmd.innerText = `${th}% / ${br}%`;

  // Hardware metrics
  const hw = frame.hardware_metrics;
  const cpuPct = Math.round(hw.cpu_utilization * 100);
  hwCpu.innerText = `${cpuPct}%`;
  hwCpuBar.style.width = `${cpuPct}%`;
  hwTemp.innerText = `${hw.temperature_celsius.toFixed(1)} °C`;
  hwThrottled.innerText = hw.is_throttled ? "THROTTLED" : "OFF";
  hwThrottled.className = hw.is_throttled ? "text-rose-400 font-semibold" : "text-emerald-400 font-semibold";
  hwMisses.innerText = hw.deadline_misses;

  let totalInFlight = 0;
  for (let q in frame.sensor_queue_depths) {
    totalInFlight += frame.sensor_queue_depths[q];
  }
  hwQueues.innerText = `${totalInFlight} packets`;

  // Safety violations overlay
  if (frame.new_violations && frame.new_violations.length > 0) {
    const latestV = frame.new_violations[0];
    safetyBanner.classList.remove("hidden");
    violationText.innerText = `${latestV.rule_name}: ${latestV.description}`;
  } else if (frame.min_clearance > 1.5) {
    safetyBanner.classList.add("hidden");
  }

  // Draw 2D Canvas
  drawCanvas(frame);
}

function drawEmptyArena() {
  const w = canvas.width;
  const h = canvas.height;
  ctx.fillStyle = "#020617";
  ctx.fillRect(0, 0, w, h);

  // Draw grid
  ctx.strokeStyle = "#1e293b";
  ctx.lineWidth = 1;
  const gridSize = w / 10;
  for (let x = 0; x < w; x += gridSize) {
    ctx.beginPath();
    ctx.moveTo(x, 0);
    ctx.lineTo(x, h);
    ctx.stroke();
  }
  for (let y = 0; y < h; y += gridSize) {
    ctx.beginPath();
    ctx.moveTo(0, y);
    ctx.lineTo(w, y);
    ctx.stroke();
  }

  // Draw Goal if scenario loaded
  if (currentScenario && currentScenario.world && currentScenario.world.goal) {
    const gx = (currentScenario.world.goal[0] / 50.0) * w;
    const gy = h - (currentScenario.world.goal[1] / 50.0) * h;
    ctx.fillStyle = "#f59e0b";
    ctx.beginPath();
    ctx.arc(gx, gy, 8, 0, 2 * Math.PI);
    ctx.fill();
    ctx.fillStyle = "#ffffff";
    ctx.font = "10px sans-serif";
    ctx.fillText("GOAL", gx - 12, gy - 12);
  }
}

function drawCanvas(frame) {
  const w = canvas.width;
  const h = canvas.height;
  const scale = w / 50.0; // 50m arena maps to canvas width

  ctx.fillStyle = "#020617";
  ctx.fillRect(0, 0, w, h);

  // Draw background grid
  ctx.strokeStyle = "#0f172a";
  ctx.lineWidth = 1;
  const gridSize = 5.0 * scale; // 5 meter grid lines
  for (let x = 0; x < w; x += gridSize) {
    ctx.beginPath();
    ctx.moveTo(x, 0);
    ctx.lineTo(x, h);
    ctx.stroke();
  }
  for (let y = 0; y < h; y += gridSize) {
    ctx.beginPath();
    ctx.moveTo(0, y);
    ctx.lineTo(w, y);
    ctx.stroke();
  }

  // Draw Goal Point
  if (currentScenario && currentScenario.world && currentScenario.world.goal) {
    const gx = currentScenario.world.goal[0] * scale;
    const gy = h - currentScenario.world.goal[1] * scale;
    ctx.fillStyle = "#fbbf24";
    ctx.beginPath();
    ctx.arc(gx, gy, 8, 0, 2 * Math.PI);
    ctx.fill();
    ctx.strokeStyle = "rgba(251, 191, 36, 0.4)";
    ctx.lineWidth = 2;
    ctx.stroke();
  }

  // Draw Static Obstacles
  if (currentScenario && currentScenario.world && currentScenario.world.obstacles) {
    currentScenario.world.obstacles
      .filter((o) => o.type !== "dynamic")
      .forEach((obs) => {
        const ox = obs.x * scale;
        const oy = h - obs.y * scale;
        const ow = (obs.length || 1.5) * scale;
        const oh = (obs.width || 1.5) * scale;
        ctx.fillStyle = "#475569";
        ctx.fillRect(ox - ow / 2, oy - oh / 2, ow, oh);
      });
  }

  // Draw Dynamic Obstacles
  if (frame.dynamic_obstacles) {
    frame.dynamic_obstacles.forEach((dyn) => {
      const dx = dyn.x * scale;
      const dy = h - dyn.y * scale;
      ctx.fillStyle = "#f43f5e";
      ctx.beginPath();
      ctx.arc(dx, dy, 7, 0, 2 * Math.PI);
      ctx.fill();
      ctx.strokeStyle = "#fda4af";
      ctx.lineWidth = 2;
      ctx.stroke();

      ctx.fillStyle = "#fda4af";
      ctx.font = "9px monospace";
      ctx.fillText(dyn.id, dx - 15, dy - 10);
    });
  }

  // Draw Rover
  const rx = frame.vehicle_state.x * scale;
  const ry = h - frame.vehicle_state.y * scale;
  const rHeading = -frame.vehicle_state.heading; // Invert Y for canvas

  ctx.save();
  ctx.translate(rx, ry);
  ctx.rotate(rHeading);

  // Clearance halo
  ctx.strokeStyle = frame.min_clearance < 1.0 ? "rgba(244, 63, 94, 0.4)" : "rgba(99, 102, 241, 0.2)";
  ctx.lineWidth = 1;
  ctx.beginPath();
  ctx.arc(0, 0, 2.0 * scale, 0, 2 * Math.PI);
  ctx.stroke();

  // Rover body box
  const rLength = 1.4 * scale;
  const rWidth = 0.9 * scale;
  ctx.fillStyle = "#6366f1";
  ctx.fillRect(-rLength / 2, -rWidth / 2, rLength, rWidth);
  ctx.strokeStyle = "#c7d2fe";
  ctx.lineWidth = 2;
  ctx.strokeRect(-rLength / 2, -rWidth / 2, rLength, rWidth);

  // Heading nose pointer
  ctx.strokeStyle = "#38bdf8";
  ctx.lineWidth = 3;
  ctx.beginPath();
  ctx.moveTo(0, 0);
  ctx.lineTo(rLength / 2 + 10, 0);
  ctx.stroke();

  ctx.restore();
}

// Start visualizer on load
window.addEventListener("DOMContentLoaded", init);
