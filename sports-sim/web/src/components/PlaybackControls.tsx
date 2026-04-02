import { useCallback, useEffect } from 'react';

interface PlaybackControlsProps {
  /** Total number of ticks available */
  totalTicks: number;
  /** Current playback position (0-based index into ticks array) */
  currentIndex: number;
  /** Whether the simulation is still streaming live */
  isLive: boolean;
  /** Whether playback is paused */
  isPaused: boolean;
  /** Playback speed multiplier */
  speed: number;
  onSeek: (index: number) => void;
  onTogglePause: () => void;
  onSpeedChange: (speed: number) => void;
  onStepForward: () => void;
  onStepBackward: () => void;
  onGoToStart: () => void;
  onGoToEnd: () => void;
}

const SPEEDS = [0.25, 0.5, 1, 2, 4, 8];

export default function PlaybackControls({
  totalTicks,
  currentIndex,
  isLive,
  isPaused,
  speed,
  onSeek,
  onTogglePause,
  onSpeedChange,
  onStepForward,
  onStepBackward,
  onGoToStart,
  onGoToEnd,
}: PlaybackControlsProps) {
  // Keyboard shortcuts
  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      // Don't capture when user is in an input/select
      if (
        e.target instanceof HTMLInputElement ||
        e.target instanceof HTMLTextAreaElement ||
        e.target instanceof HTMLSelectElement
      )
        return;

      switch (e.key) {
        case ' ':
          e.preventDefault();
          onTogglePause();
          break;
        case 'ArrowLeft':
          e.preventDefault();
          onStepBackward();
          break;
        case 'ArrowRight':
          e.preventDefault();
          onStepForward();
          break;
        case 'Home':
          e.preventDefault();
          onGoToStart();
          break;
        case 'End':
          e.preventDefault();
          onGoToEnd();
          break;
        case '[':
          e.preventDefault();
          onSpeedChange(Math.max(0.25, speed / 2));
          break;
        case ']':
          e.preventDefault();
          onSpeedChange(Math.min(8, speed * 2));
          break;
      }
    },
    [onTogglePause, onStepForward, onStepBackward, onGoToStart, onGoToEnd, onSpeedChange, speed],
  );

  useEffect(() => {
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [handleKeyDown]);

  return (
    <div className="bg-gray-800 rounded-xl p-3 space-y-2">
      {/* Progress bar */}
      <div className="flex items-center gap-2 text-xs text-gray-400">
        <span className="tabular-nums w-12 text-right">{currentIndex + 1}</span>
        <input
          type="range"
          min={0}
          max={Math.max(totalTicks - 1, 0)}
          value={currentIndex}
          onChange={(e) => onSeek(Number(e.target.value))}
          className="flex-1 accent-blue-500 h-1.5"
          aria-label="Playback position"
        />
        <span className="tabular-nums w-12">{totalTicks}</span>
        {isLive && (
          <span className="bg-red-600 text-white text-[10px] font-bold px-1.5 py-0.5 rounded animate-pulse">
            LIVE
          </span>
        )}
      </div>

      {/* Controls row */}
      <div className="flex items-center justify-center gap-1">
        <button
          onClick={onGoToStart}
          className="p-1.5 rounded hover:bg-gray-700 text-gray-400 hover:text-white transition-colors"
          title="Go to start (Home)"
          aria-label="Go to start"
        >
          <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
            <path d="M3 3v10h2V3H3zM7 8l6 5V3L7 8z" />
          </svg>
        </button>

        <button
          onClick={onStepBackward}
          className="p-1.5 rounded hover:bg-gray-700 text-gray-400 hover:text-white transition-colors"
          title="Step back (←)"
          aria-label="Step backward"
        >
          <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
            <path d="M10 3L4 8l6 5V3z" />
          </svg>
        </button>

        <button
          onClick={onTogglePause}
          className="p-2 rounded-full bg-blue-600 hover:bg-blue-500 text-white transition-colors"
          title={isPaused ? 'Play (Space)' : 'Pause (Space)'}
          aria-label={isPaused ? 'Play' : 'Pause'}
        >
          {isPaused ? (
            <svg width="20" height="20" viewBox="0 0 20 20" fill="currentColor">
              <path d="M6 4l10 6-10 6V4z" />
            </svg>
          ) : (
            <svg width="20" height="20" viewBox="0 0 20 20" fill="currentColor">
              <path d="M5 4h3v12H5V4zM12 4h3v12h-3V4z" />
            </svg>
          )}
        </button>

        <button
          onClick={onStepForward}
          className="p-1.5 rounded hover:bg-gray-700 text-gray-400 hover:text-white transition-colors"
          title="Step forward (→)"
          aria-label="Step forward"
        >
          <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
            <path d="M6 3v10l6-5-6-5z" />
          </svg>
        </button>

        <button
          onClick={onGoToEnd}
          className="p-1.5 rounded hover:bg-gray-700 text-gray-400 hover:text-white transition-colors"
          title="Go to end (End)"
          aria-label="Go to end"
        >
          <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
            <path d="M3 3l6 5-6 5V3zM11 3v10h2V3h-2z" />
          </svg>
        </button>

        {/* Speed selector */}
        <div className="ml-3 flex items-center gap-1 text-xs text-gray-400">
          {SPEEDS.map((s) => (
            <button
              key={s}
              onClick={() => onSpeedChange(s)}
              className={`px-1.5 py-0.5 rounded transition-colors ${
                speed === s
                  ? 'bg-blue-600 text-white'
                  : 'hover:bg-gray-700 hover:text-white'
              }`}
              aria-label={`${s}x speed`}
            >
              {s}x
            </button>
          ))}
        </div>
      </div>

      {/* Keyboard hint */}
      <p className="text-[10px] text-gray-600 text-center hidden md:block">
        Space: play/pause · ←/→: step · Home/End: jump · [/]: speed
      </p>
    </div>
  );
}
