import { useMemo } from 'react';
import type { SportType, StreamTick } from '../types';
import { getAccentFillColor } from '../sportUi';

interface Props {
  sport: SportType;
  ticks: StreamTick[];
}

export default function ScoreChart({ sport, ticks }: Props) {
  const accent = getAccentFillColor(sport);

  const { points, width, height, homeColor, awayColor } = useMemo(() => {
    const w = 400;
    const h = 120;
    if (ticks.length < 2) return { points: [], maxScore: 1, width: w, height: h, homeColor: accent, awayColor: '#ef4444' };

    const maxS = Math.max(
      1,
      ...ticks.map((t) => Math.max(t.home_score, t.away_score)),
    );
    const pts = ticks.map((t, i) => ({
      x: (i / (ticks.length - 1)) * w,
      homeY: h - (t.home_score / maxS) * (h - 20) - 10,
      awayY: h - (t.away_score / maxS) * (h - 20) - 10,
      home: t.home_score,
      away: t.away_score,
    }));
    return { points: pts, maxScore: maxS, width: w, height: h, homeColor: accent, awayColor: '#ef4444' };
  }, [ticks, accent]);

  if (ticks.length < 2) return null;

  const homePath = `M ${points.map((p) => `${p.x},${p.homeY}`).join(' L ')}`;
  const awayPath = `M ${points.map((p) => `${p.x},${p.awayY}`).join(' L ')}`;

  return (
    <figure className="rounded-2xl border border-white/8 bg-slate-900/85 p-4 backdrop-blur-sm">
      <h3 className="text-xs font-medium uppercase tracking-wider text-slate-500 mb-2">Score Progression</h3>
      <svg viewBox={`0 0 ${width} ${height}`} className="w-full" preserveAspectRatio="none" role="img" aria-label={`Score progression: ${ticks[ticks.length - 1]?.home_team} ${ticks[ticks.length - 1]?.home_score}, ${ticks[ticks.length - 1]?.away_team} ${ticks[ticks.length - 1]?.away_score}`}>
        {/* Grid lines */}
        {[0.25, 0.5, 0.75].map((f) => (
          <line
            key={f}
            x1={0} y1={height - f * (height - 20) - 10}
            x2={width} y2={height - f * (height - 20) - 10}
            stroke="rgba(255,255,255,0.05)"
            strokeDasharray="4 4"
          />
        ))}
        {/* Home score line */}
        <path d={homePath} fill="none" stroke={homeColor} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
        {/* Away score line */}
        <path d={awayPath} fill="none" stroke={awayColor} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" opacity="0.8" />
      </svg>
      <div className="flex gap-4 mt-2 text-xs">
        <div className="flex items-center gap-1.5">
          <svg className="inline-block w-3 h-1" viewBox="0 0 12 2" aria-hidden="true">
            <rect width="12" height="2" rx="1" fill={homeColor} />
          </svg>
          <span className="text-slate-400">{ticks[ticks.length - 1]?.home_team ?? 'Home'} ({ticks[ticks.length - 1]?.home_score})</span>
        </div>
        <div className="flex items-center gap-1.5">
          <svg className="inline-block w-3 h-1" viewBox="0 0 12 2" aria-hidden="true">
            <rect width="12" height="2" rx="1" fill={awayColor} />
          </svg>
          <span className="text-slate-400">{ticks[ticks.length - 1]?.away_team ?? 'Away'} ({ticks[ticks.length - 1]?.away_score})</span>
        </div>
      </div>
    </figure>
  );
}
