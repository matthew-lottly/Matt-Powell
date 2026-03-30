import type { StreamTick, SportType } from '../types';
import { SPORT_LABELS } from '../types';

interface Props {
  tick: StreamTick | null;
  sport: SportType;
}

export default function Scoreboard({ tick, sport }: Props) {
  if (!tick) {
    return (
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-6 text-center text-gray-500">
        Press <span className="font-semibold text-gray-300">Start</span> to begin
      </div>
    );
  }

  const periodLabel =
    sport === 'soccer'
      ? `Half ${tick.period}`
      : sport === 'basketball'
        ? `Q${tick.period}`
        : sport === 'football'
          ? `Q${tick.period}`
          : sport === 'hockey'
            ? `Period ${tick.period}`
            : sport === 'tennis'
              ? `Set ${tick.period}`
              : sport === 'golf'
                ? `Hole ${tick.period}`
                : sport === 'cricket'
                  ? `Over ${tick.period}`
                  : sport === 'boxing' || sport === 'mma'
                    ? `Round ${tick.period}`
                    : sport === 'racing'
                      ? `Lap ${tick.period}`
                      : `Inning ${tick.period}`;

  return (
    <div className="bg-gray-900 border border-gray-800 rounded-xl p-4">
      <div className="text-xs text-center text-gray-500 mb-1">
        {SPORT_LABELS[sport]} · {periodLabel} · {tick.clock.toFixed(1)} min
      </div>
      <div className="flex items-center justify-center gap-4 text-3xl font-extrabold tabular-nums">
        <div className="text-right">
          <div className="text-xs text-blue-300 font-normal">{tick.home_team}</div>
          <span className="text-blue-400">{tick.home_score}</span>
        </div>
        <span className="text-gray-600">–</span>
        <div className="text-left">
          <div className="text-xs text-red-300 font-normal">{tick.away_team}</div>
          <span className="text-red-400">{tick.away_score}</span>
        </div>
      </div>
      {tick.is_finished && (
        <div className="text-center mt-2 text-green-400 text-xs font-semibold uppercase tracking-wider">
          Final
        </div>
      )}
    </div>
  );
}
