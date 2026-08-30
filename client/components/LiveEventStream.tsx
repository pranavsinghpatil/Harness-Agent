"use client";

import React, { useState, useRef, useEffect, useMemo, useCallback } from "react";
import { HarnessEvent, EventSeverity } from "../types/simulation";

interface LiveEventStreamProps {
  events: HarnessEvent[];
  maxDisplay?: number;
}

type FilterCategory = "ALL" | "SYSTEM_2" | "SYSTEM_1" | "SAFETY";

const SYSTEM_2_TYPES = new Set<string>([
  "INVESTIGATION_CREATED",
  "INVESTIGATION_STARTED",
  "EXPERIMENT_PLANNED",
  "EXPERIMENT_STARTED",
  "EXPERIMENT_COMPLETED",
  "EVIDENCE_CAPTURED",
  "HYPOTHESIS_UPDATED",
  "FALSIFICATION_PROPOSED",
  "DECISION_RECORDED",
  "NEXT_EXPERIMENT_SELECTED",
  "INVESTIGATION_COMPLETED",
  "INVESTIGATION_FAILED",
  "DIAGNOSIS_COMPLETED",
  "PATCH_GENERATED",
  "PATCH_APPROVAL_REQUESTED",
  "PATCH_APPROVED",
  "PATCH_REJECTED",
  "VERIFICATION_PASSED",
  "VERIFICATION_FAILED",
  "REGRESSION_STARTED",
  "REGRESSION_COMPLETED",
  "CONCLUSION_RECORDED",
]);

const SYSTEM_1_TYPES = new Set<string>([
  "SIMULATION_STARTED",
  "SIMULATION_STEP",
  "SIMULATION_TERMINATED",
  "FAULT_INJECTED",
  "FAULT_REVERTED",
  "SENSOR_SAMPLED",
  "PACKET_QUEUED",
  "PACKET_DELIVERED",
  "PACKET_DROPPED",
  "TASK_SCHEDULED",
  "PERCEPTION_TASK_SCHEDULED",
  "CONTROLLER_TASK_SCHEDULED",
  "OBSERVATION_AVAILABLE",
  "TASK_REJECTED",
  "COMPUTE_STARTED",
  "TASK_COMPLETED",
  "DEADLINE_MISSED",
  "THERMAL_THROTTLED",
  "COMMAND_ISSUED",
  "ACTUATOR_APPLIED",
  "CONTROLLER_EXCEPTION",
  "CONTROLLER_CRASHED",
  "INVARIANT_BREACHED",
  "COLLISION_DETECTED",
  "CLEARANCE_WARNING",
]);

function isSystem2(type: string): boolean {
  if (SYSTEM_2_TYPES.has(type)) return true;
  return (
    type.startsWith("INVESTIGATION_") ||
    type.startsWith("EXPERIMENT_") ||
    type.startsWith("HYPOTHESIS_") ||
    type.startsWith("FALSIFICATION_") ||
    type.startsWith("DECISION_") ||
    type.startsWith("NEXT_") ||
    type.startsWith("DIAGNOSIS_") ||
    type.startsWith("PATCH_") ||
    type.startsWith("VERIFICATION_") ||
    type.startsWith("REGRESSION_") ||
    type.startsWith("CONCLUSION_")
  );
}

function isSystem1(type: string): boolean {
  if (SYSTEM_1_TYPES.has(type)) return true;
  return (
    type.startsWith("SIMULATION_") ||
    type.startsWith("SENSOR_") ||
    type.startsWith("PACKET_") ||
    type.startsWith("TASK_") ||
    type.startsWith("PERCEPTION_") ||
    type.startsWith("CONTROLLER_") ||
    type.startsWith("OBSERVATION_") ||
    type.startsWith("COMPUTE_") ||
    type.startsWith("COMMAND_") ||
    type.startsWith("ACTUATOR_") ||
    type.startsWith("FAULT_")
  );
}

function isSafety(ev: HarnessEvent): boolean {
  if (ev.severity === "CRITICAL" || ev.severity === "ERROR") return true;
  const t = ev.type;
  return (
    t.includes("VIOLATION") ||
    t.includes("BREACH") ||
    t.includes("COLLISION") ||
    t.includes("CLEARANCE") ||
    t.includes("DEADLINE") ||
    t.includes("THROTTLE") ||
    t.includes("FAILED") ||
    t.includes("EXCEPTION") ||
    t.includes("CRASHED")
  );
}

// Cached string representation of event payload objects for fast search
const payloadStringCache = new WeakMap<object, string>();
function getPayloadString(payload: Record<string, unknown> | undefined): string {
  if (!payload || typeof payload !== "object") return "";
  let cached = payloadStringCache.get(payload);
  if (cached === undefined) {
    cached = JSON.stringify(payload).toLowerCase();
    payloadStringCache.set(payload, cached);
  }
  return cached;
}

const getSeverityBadge = (sev: EventSeverity) => {
  switch (sev) {
    case "CRITICAL":
    case "ERROR":
      return "bg-rose-500/20 text-rose-300 border-rose-500/40";
    case "WARNING":
      return "bg-amber-500/20 text-amber-300 border-amber-500/40";
    case "INFO":
      return "bg-indigo-500/20 text-indigo-300 border-indigo-500/40";
    default:
      return "bg-slate-800 text-slate-400 border-slate-700";
  }
};

const formatTime = (simTime: number, wallTime: number) => {
  if (simTime > 0) {
    return `T+${simTime.toFixed(2)}s`;
  }
  if (wallTime > 0) {
    const d = new Date(wallTime * 1000);
    return d.toTimeString().split(" ")[0];
  }
  return "00:00";
};

interface EventRowProps {
  ev: HarnessEvent;
  isExpanded: boolean;
  onToggle: (id: string) => void;
}

const EventRow = React.memo(function EventRow({
  ev,
  isExpanded,
  onToggle,
}: EventRowProps) {
  const hasPayload = ev.payload && Object.keys(ev.payload).length > 0;
  const payloadPreview = useMemo(() => {
    if (!hasPayload || isExpanded) return "";
    return JSON.stringify(ev.payload);
  }, [ev.payload, hasPayload, isExpanded]);

  return (
    <div
      className="bg-slate-950/60 hover:bg-slate-950 border border-slate-800/80 hover:border-slate-700 rounded-lg p-2 transition cursor-pointer"
      onClick={() => onToggle(ev.event_id)}
    >
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2 flex-wrap">
          {/* Timestamp */}
          <span className="text-[10px] text-slate-500 min-w-13.75">
            {formatTime(ev.sim_time, ev.wall_time)}
          </span>

          {/* Severity Badge */}
          <span
            className={`px-1.5 py-0.5 rounded text-[9px] font-semibold border ${getSeverityBadge(
              ev.severity
            )}`}
          >
            {ev.severity}
          </span>

          {/* Event Type */}
          <span className="text-slate-200 font-semibold text-[11px]">
            {ev.type}
          </span>

          {/* Source */}
          <span className="text-slate-500 text-[10px]">[{ev.source}]</span>
        </div>

        {/* Summary / Expand Hint */}
        <span className="text-[10px] text-indigo-400 font-sans">
          {isExpanded ? "▲ Hide Payload" : "▼ Inspect"}
        </span>
      </div>

      {/* Brief preview if not expanded */}
      {!isExpanded && hasPayload && (
        <p className="text-[10px] text-slate-400 font-mono mt-1 truncate">
          {payloadPreview}
        </p>
      )}

      {/* Expanded JSON Inspector */}
      {isExpanded && (
        <div className="mt-2 pt-2 border-t border-slate-800/80 bg-slate-950 rounded p-2 text-[10px] text-slate-300 overflow-x-auto">
          <pre>{JSON.stringify(ev, null, 2)}</pre>
        </div>
      )}
    </div>
  );
});

export const LiveEventStream: React.FC<LiveEventStreamProps> = ({
  events,
  maxDisplay = 500,
}) => {
  const [filterCategory, setFilterCategory] = useState<FilterCategory>("ALL");
  const [searchQuery, setSearchQuery] = useState<string>("");
  const [autoScroll, setAutoScroll] = useState<boolean>(true);
  const [expandedEventId, setExpandedEventId] = useState<string | null>(null);

  const scrollContainerRef = useRef<HTMLDivElement | null>(null);

  // Filter events based on active category and search
  const filteredEvents = useMemo(() => {
    const query = searchQuery.trim().toLowerCase();

    return events.filter((ev) => {
      // Category filter
      if (filterCategory === "SYSTEM_2") {
        if (!isSystem2(ev.type)) return false;
      } else if (filterCategory === "SYSTEM_1") {
        if (!isSystem1(ev.type)) return false;
      } else if (filterCategory === "SAFETY") {
        if (!isSafety(ev)) return false;
      }

      // Search filter
      if (query) {
        const matchesType = ev.type.toLowerCase().includes(query);
        const matchesSource = ev.source.toLowerCase().includes(query);
        const matchesPayload = getPayloadString(ev.payload).includes(query);
        return matchesType || matchesSource || matchesPayload;
      }

      return true;
    });
  }, [events, filterCategory, searchQuery]);

  // High performance auto-scroll when new events arrive
  useEffect(() => {
    if (autoScroll && scrollContainerRef.current) {
      scrollContainerRef.current.scrollTop = scrollContainerRef.current.scrollHeight;
    }
  }, [filteredEvents, autoScroll]);

  const handleToggleExpand = useCallback((eventId: string) => {
    setExpandedEventId((prev) => (prev === eventId ? null : eventId));
  }, []);

  const displaySlice = useMemo(() => {
    return filteredEvents.length > maxDisplay
      ? filteredEvents.slice(-maxDisplay)
      : filteredEvents;
  }, [filteredEvents, maxDisplay]);

  return (
    <div className="bg-slate-900/90 backdrop-blur-md border border-slate-800 rounded-2xl flex flex-col h-full shadow-2xl overflow-hidden">
      {/* Feed Controls Header */}
      <div className="p-3 sm:p-4 border-b border-slate-800 space-y-3">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full bg-indigo-500 animate-pulse"></span>
            <h3 className="text-xs font-bold text-slate-100 uppercase tracking-wider">
              Canonical Event Stream
            </h3>
            <span className="px-2 py-0.5 rounded-full bg-slate-800 text-slate-400 font-mono text-[10px]">
              {filteredEvents.length} events
            </span>
          </div>

          {/* Auto-scroll toggle */}
          <label className="flex items-center gap-1.5 text-[11px] text-slate-400 cursor-pointer select-none">
            <input
              type="checkbox"
              checked={autoScroll}
              onChange={(e) => setAutoScroll(e.target.checked)}
              className="rounded bg-slate-800 border-slate-700 text-indigo-600 focus:ring-0 cursor-pointer"
            />
            <span>Auto-scroll</span>
          </label>
        </div>

        {/* Category Tabs & Search Bar */}
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div className="flex items-center gap-1 bg-slate-950 p-1 rounded-xl border border-slate-800 text-[11px]">
            {(
              [
                { id: "ALL", label: "All Events" },
                { id: "SYSTEM_2", label: "System 2 Reasoning" },
                { id: "SYSTEM_1", label: "System 1 Physics" },
                { id: "SAFETY", label: "Safety & Invariants" },
              ] as const
            ).map((cat) => (
              <button
                key={cat.id}
                onClick={() => setFilterCategory(cat.id)}
                className={`px-2.5 py-1 rounded-lg font-medium transition cursor-pointer ${
                  filterCategory === cat.id
                    ? "bg-indigo-600 text-white shadow-sm"
                    : "text-slate-400 hover:text-slate-200"
                }`}
              >
                {cat.label}
              </button>
            ))}
          </div>

          <div className="relative">
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search event type, source, payload..."
              className="bg-slate-950 border border-slate-800 rounded-lg px-3 py-1 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-indigo-500 w-48 sm:w-64"
            />
            {searchQuery && (
              <button
                onClick={() => setSearchQuery("")}
                className="absolute right-2 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300 text-xs"
              >
                ✕
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Events Scroll Area */}
      <div
        ref={scrollContainerRef}
        className="flex-1 overflow-y-auto p-3 space-y-1.5 font-mono text-xs max-h-105 `sm:max-h-125"
      >
        {displaySlice.length === 0 ? (
          <div className="py-12 text-center text-slate-500 text-xs font-sans">
            No events recorded yet. Start an investigation to stream real-time events.
          </div>
        ) : (
          displaySlice.map((ev, idx) => (
            <EventRow
              key={ev.event_id || idx}
              ev={ev}
              isExpanded={expandedEventId === ev.event_id}
              onToggle={handleToggleExpand}
            />
          ))
        )}
      </div>
    </div>
  );
};
