import type { StreamTick } from '../../types';

interface Props {
  tick: StreamTick | null;
}

/** Top-down SVG cricket ground — circular field */
export default function CricketField({ tick: _tick }: Props) {
  const W = 360;
  const H = 360;
  const cx = W / 2;
  const cy = H / 2;
  const outerR = 160;
  const innerR = 100;
  const pitchW = 8;
  const pitchH = 60;

  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="w-full max-w-[400px]" aria-label="Cricket field">
      {/* Outfield */}
      <circle cx={cx} cy={cy} r={outerR} fill="#2e7d32" />

      {/* Inner circle (30-yard) */}
      <circle cx={cx} cy={cy} r={innerR} fill="none" stroke="white" strokeWidth={1} strokeDasharray="4 3" />

      {/* Boundary */}
      <circle cx={cx} cy={cy} r={outerR} fill="none" stroke="white" strokeWidth={2} />

      {/* Pitch (centre strip) */}
      <rect x={cx - pitchW / 2} y={cy - pitchH / 2} width={pitchW} height={pitchH}
        fill="#c8a96e" stroke="#a0844e" strokeWidth={0.8} />

      {/* Crease lines */}
      <line x1={cx - 14} y1={cy - pitchH / 2 + 6} x2={cx + 14} y2={cy - pitchH / 2 + 6}
        stroke="white" strokeWidth={1} />
      <line x1={cx - 14} y1={cy + pitchH / 2 - 6} x2={cx + 14} y2={cy + pitchH / 2 - 6}
        stroke="white" strokeWidth={1} />

      {/* Stumps */}
      {[cy - pitchH / 2 + 6, cy + pitchH / 2 - 6].map((sy, i) => (
        <g key={i}>
          <line x1={cx - 3} y1={sy - 4} x2={cx - 3} y2={sy} stroke="#8d6e63" strokeWidth={1} />
          <line x1={cx} y1={sy - 4} x2={cx} y2={sy} stroke="#8d6e63" strokeWidth={1} />
          <line x1={cx + 3} y1={sy - 4} x2={cx + 3} y2={sy} stroke="#8d6e63" strokeWidth={1} />
        </g>
      ))}

      {/* Fielding positions (subtle dots) */}
      {[
        [cx, cy - 120], [cx, cy + 120],
        [cx - 100, cy - 70], [cx + 100, cy - 70],
        [cx - 100, cy + 70], [cx + 100, cy + 70],
        [cx - 140, cy], [cx + 140, cy],
        [cx - 50, cy - 40], [cx + 50, cy - 40],
      ].map(([x, y], i) => (
        <circle key={i} cx={x} cy={y} r={3} fill="rgba(255,255,255,0.25)" />
      ))}

      {/* Score overlay */}
      {_tick && (
        <text x={cx} y={20} textAnchor="middle" fontSize={9} fill="rgba(255,255,255,0.6)">
          Over {_tick.period} · {_tick.home_score}/{_tick.away_score}
        </text>
      )}
    </svg>
  );
}
