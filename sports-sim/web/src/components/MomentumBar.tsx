import type { StreamTick } from '../types';
import type { SportType } from '../types';
import { getSportMomentumLabel } from '../sportUi';

interface Props {
  tick: StreamTick | null;
  sport: SportType;
}

export default function MomentumBar({ tick, sport }: Props) {
  if (!tick) return null;

  const homeWidth = Math.max(0, Math.min(50, Math.round(tick.home_momentum * 50)));
  const awayWidth = Math.max(0, Math.min(50, Math.round(tick.away_momentum * 50)));
  const label = getSportMomentumLabel(sport);

  return (
    <section aria-label="Momentum" className="rounded-2xl border border-white/8 bg-slate-900/85 px-4 py-3 backdrop-blur-sm">
      <div className="mb-2 flex items-center justify-between text-[11px] uppercase tracking-[0.16em] text-slate-500">
        <span>{label}</span>
        <span>{tick.home_team} vs {tick.away_team}</span>
      </div>
      <div className="flex items-center gap-3 text-xs">
        <span className="text-blue-400 w-20 text-right">{tick.home_team}</span>
        <svg viewBox="0 0 100 12" preserveAspectRatio="none" className="flex-1 h-3 overflow-hidden rounded-full bg-gray-800" role="img" aria-label={`${tick.home_team} momentum ${Math.round(tick.home_momentum * 100)}%, ${tick.away_team} momentum ${Math.round(tick.away_momentum * 100)}%`}>
          <rect x="0" y="0" width="100" height="12" rx="6" fill="#1f2937" />
          <rect x="0" y="0" width={homeWidth} height="12" rx="6" fill="rgba(59, 130, 246, 0.6)" />
          <rect x={100 - awayWidth} y="0" width={awayWidth} height="12" rx="6" fill="rgba(239, 68, 68, 0.6)" />
          <rect x="49.5" y="0" width="1" height="12" fill="#4b5563" />
        </svg>
        <span className="text-red-400 w-20">{tick.away_team}</span>
      </div>
    </section>
  );
}
