import type { StreamTick } from '../../types';

interface Props {
  tick: StreamTick | null;
}

/** Top-down SVG soccer pitch — 105 × 68 m scaled to viewBox */
export default function SoccerField({ tick: _tick }: Props) {
  const W = 420;
  const H = 272;

  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="w-full max-w-[560px]" aria-label="Soccer pitch">
      {/* Grass */}
      <rect width={W} height={H} rx={6} className="fill-field-soccer" />

      {/* Outline */}
      <rect x={10} y={10} width={W - 20} height={H - 20} fill="none" stroke="white" strokeWidth={1.5} rx={2} />

      {/* Center line */}
      <line x1={W / 2} y1={10} x2={W / 2} y2={H - 10} stroke="white" strokeWidth={1} />

      {/* Center circle */}
      <circle cx={W / 2} cy={H / 2} r={36} fill="none" stroke="white" strokeWidth={1} />
      <circle cx={W / 2} cy={H / 2} r={2} fill="white" />

      {/* Left penalty area */}
      <rect x={10} y={H / 2 - 66} width={64} height={132} fill="none" stroke="white" strokeWidth={1} />
      <rect x={10} y={H / 2 - 30} width={22} height={60} fill="none" stroke="white" strokeWidth={1} />
      <circle cx={46} cy={H / 2} r={2} fill="white" />

      {/* Right penalty area */}
      <rect x={W - 74} y={H / 2 - 66} width={64} height={132} fill="none" stroke="white" strokeWidth={1} />
      <rect x={W - 32} y={H / 2 - 30} width={22} height={60} fill="none" stroke="white" strokeWidth={1} />
      <circle cx={W - 46} cy={H / 2} r={2} fill="white" />

      {/* Corner arcs */}
      {[
        [10, 10],
        [W - 10, 10],
        [10, H - 10],
        [W - 10, H - 10],
      ].map(([cx, cy], i) => (
        <path
          key={i}
          d={`M ${cx! + (cx === 10 ? 8 : -8)},${cy} A 8,8 0 0,${cy === 10 ? (cx === 10 ? 1 : 0) : cx === 10 ? 0 : 1} ${cx},${cy! + (cy === 10 ? 8 : -8)}`}
          fill="none"
          stroke="white"
          strokeWidth={0.8}
        />
      ))}

      {/* Status overlay */}
      {_tick && (
        <text x={W / 2} y={18} textAnchor="middle" fontSize={8} fill="rgba(255,255,255,0.5)">
          {_tick.home_score} – {_tick.away_score}
        </text>
      )}
    </svg>
  );
}
