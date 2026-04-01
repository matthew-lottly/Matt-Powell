import type { StreamTick } from '../types';

interface Props {
  tick: StreamTick | null;
}

export default function MomentumBar({ tick }: Props) {
  if (!tick) return null;

  const homeWidth = Math.max(0, Math.min(50, Math.round(tick.home_momentum * 50)));
  const awayWidth = Math.max(0, Math.min(50, Math.round(tick.away_momentum * 50)));

  return (
    <div className="flex items-center gap-3 text-xs">
      <span className="text-blue-400 w-20 text-right">Home</span>
      <div className="flex-1 h-3 bg-gray-800 rounded-full overflow-hidden relative">
        {/* Home momentum (left → center) */}
        <div
          className="absolute inset-y-0 left-0 bg-blue-500/60 transition-all"
          style={{ width: `${homeWidth}%` }}
        />
        {/* Away momentum (right → center) */}
        <div
          className="absolute inset-y-0 right-0 bg-red-500/60 transition-all"
          style={{ width: `${awayWidth}%` }}
        />
        {/* Center line */}
        <div className="absolute inset-y-0 left-1/2 w-px bg-gray-600" />
      </div>
      <span className="text-red-400 w-20">Away</span>
    </div>
  );
}
