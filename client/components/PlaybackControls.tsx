"use client";

import React from "react";

interface PlaybackControlsProps {
  isPlaying: boolean;
  onPlayPauseToggle: () => void;
  currentFrameIdx: number;
  totalFrames: number;
  onScrub: (index: number) => void;
  playbackSpeed: number;
  onSpeedChange: (speed: number) => void;
  currentTime: number;
  totalDuration: number;
}

export const PlaybackControls: React.FC<PlaybackControlsProps> = ({
  isPlaying,
  onPlayPauseToggle,
  currentFrameIdx,
  totalFrames,
  onScrub,
  playbackSpeed,
  onSpeedChange,
  currentTime,
  totalDuration,
}) => {
  const maxIdx = Math.max(0, totalFrames - 1);
  const speeds = [0.5, 1, 2, 5];

  const handleStepBack = () => {
    onScrub(Math.max(0, currentFrameIdx - 1));
  };

  const handleStepForward = () => {
    onScrub(Math.min(maxIdx, currentFrameIdx + 1));
  };

  return (
    <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-3.5 shadow-xl flex flex-wrap items-center justify-between gap-3">
      {/* Play/Pause & Step Controls */}
      <div className="flex items-center space-x-2">
        <button
          onClick={handleStepBack}
          disabled={currentFrameIdx <= 0 || totalFrames === 0}
          title="Step Backward"
          className="p-2 rounded-lg bg-slate-800 hover:bg-slate-700 disabled:opacity-40 text-slate-300 transition cursor-pointer"
        >
          <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
            <path d="M8.445 14.832A1 1 0 0010 14v-2.798l5.445 3.63A1 1 0 0017 14V6a1 1 0 00-1.555-.832L10 8.798V6a1 1 0 00-1.555-.832l-6 4a1 1 0 000 1.664l6 4z" />
          </svg>
        </button>

        <button
          onClick={onPlayPauseToggle}
          disabled={totalFrames === 0}
          title={isPlaying ? "Pause" : "Play"}
          className="p-2.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 active:bg-indigo-700 disabled:opacity-40 text-white shadow-lg shadow-indigo-600/30 transition cursor-pointer"
        >
          {isPlaying ? (
            <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
              <path
                fillRule="evenodd"
                d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zM7 8a1 1 0 012 0v4a1 1 0 11-2 0V8zm5-1a1 1 0 00-1 1v4a1 1 0 102 0V8a1 1 0 00-1-1z"
                clipRule="evenodd"
              />
            </svg>
          ) : (
            <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
              <path
                fillRule="evenodd"
                d="M10 18a8 8 0 100-16 8 8 0 000 16zM9.555 7.168A1 1 0 008 8v4a1 1 0 001.555.832l3-2a1 1 0 000-1.664l-3-2z"
                clipRule="evenodd"
              />
            </svg>
          )}
        </button>

        <button
          onClick={handleStepForward}
          disabled={currentFrameIdx >= maxIdx || totalFrames === 0}
          title="Step Forward"
          className="p-2 rounded-lg bg-slate-800 hover:bg-slate-700 disabled:opacity-40 text-slate-300 transition cursor-pointer"
        >
          <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
            <path d="M11.555 5.168A1 1 0 0010 6v2.798L4.555 5.168A1 1 0 003 6v8a1 1 0 001.555.832L10 11.202V14a1 1 0 001.555.832l6-4a1 1 0 000-1.664l-6-4z" />
          </svg>
        </button>
      </div>

      {/* Scrubber Range Slider */}
      <div className="flex-1 min-w-[180px] flex items-center space-x-3">
        <input
          type="range"
          min={0}
          max={maxIdx}
          value={totalFrames === 0 ? 0 : currentFrameIdx}
          onChange={(e) => onScrub(parseInt(e.target.value, 10) || 0)}
          disabled={totalFrames === 0}
          className="flex-1 h-2 bg-slate-950 rounded-lg appearance-none cursor-pointer accent-indigo-500 disabled:opacity-40"
        />
        <span className="text-xs font-mono text-slate-300 w-24 text-right">
          {currentTime.toFixed(2)}s{" "}
          <span className="text-slate-500">/ {totalDuration.toFixed(2)}s</span>
        </span>
      </div>

      {/* Speed Multiplier Pill */}
      <div className="flex items-center bg-slate-950 p-1 rounded-lg border border-slate-800 text-[11px] font-mono">
        {speeds.map((s) => (
          <button
            key={s}
            onClick={() => onSpeedChange(s)}
            className={`px-2 py-0.5 rounded transition ${
              playbackSpeed === s
                ? "bg-indigo-600 text-white font-bold"
                : "text-slate-400 hover:text-slate-200"
            }`}
          >
            {s}x
          </button>
        ))}
      </div>
    </div>
  );
};

