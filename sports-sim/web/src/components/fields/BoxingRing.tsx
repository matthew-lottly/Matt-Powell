import type { StreamTick } from '../../types';

interface Props {
  tick: StreamTick | null;
}

/** Top-down SVG boxing ring */
export default function BoxingRing({ tick: _tick }: Props) {
  const W = 320;
  const H = 320;
  const cx = W / 2;
  const cy = H / 2;
  const ringSize = 240;
  const ringL = (W - ringSize) / 2;
  const ringT = (H - ringSize) / 2;

  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="w-full max-w-[400px]" aria-label="Boxing ring">
      {/* Platform */}
      <rect x={ringL - 10} y={ringT - 10} width={ringSize + 20} height={ringSize + 20}
        rx={4} fill="#5d4037" />

      {/* Canvas */}
      <rect x={ringL} y={ringT} width={ringSize} height={ringSize}
        rx={2} fill="#e8e0d4" stroke="#8d6e63" strokeWidth={2} />

      {/* Ring ropes — 3 strands */}
      {[0.12, 0.5, 0.88].map((t, i) => {
        const inset = ringSize * t;
        return (
          <g key={i}>
            {/* Top */}
            <line x1={ringL} y1={ringT + inset * 0.08 + 2} x2={ringL + ringSize} y2={ringT + inset * 0.08 + 2}
              stroke={i === 1 ? '#d32f2f' : '#ccc'} strokeWidth={1.5} opacity={0.5 + i * 0.15} />
            {/* Bottom */}
            <line x1={ringL} y1={ringT + ringSize - inset * 0.08 - 2} x2={ringL + ringSize}
              y2={ringT + ringSize - inset * 0.08 - 2}
              stroke={i === 1 ? '#d32f2f' : '#ccc'} strokeWidth={1.5} opacity={0.5 + i * 0.15} />
          </g>
        );
      })}

      {/* Ring border ropes */}
      <rect x={ringL + 3} y={ringT + 3} width={ringSize - 6} height={ringSize - 6}
        fill="none" stroke="#d32f2f" strokeWidth={2} rx={1} />
      <rect x={ringL + 8} y={ringT + 8} width={ringSize - 16} height={ringSize - 16}
        fill="none" stroke="#fff" strokeWidth={1} rx={1} />
      <rect x={ringL + 13} y={ringT + 13} width={ringSize - 26} height={ringSize - 26}
        fill="none" stroke="#1565c0" strokeWidth={1.5} rx={1} />

      {/* Corner posts */}
      {[
        [ringL, ringT], [ringL + ringSize, ringT],
        [ringL, ringT + ringSize], [ringL + ringSize, ringT + ringSize],
      ].map(([x, y], i) => (
        <circle key={i} cx={x} cy={y} r={5}
          fill={i < 2 ? '#d32f2f' : '#1565c0'} stroke="#333" strokeWidth={1} />
      ))}

      {/* Center circle */}
      <circle cx={cx} cy={cy} r={30} fill="none" stroke="rgba(0,0,0,0.1)" strokeWidth={1} />

      {/* Neutral corners - labels */}
      <text x={ringL + 16} y={ringT + 24} fontSize={7} fill="rgba(0,0,0,0.3)">RED</text>
      <text x={ringL + ringSize - 36} y={ringT + ringSize - 14} fontSize={7} fill="rgba(0,0,0,0.3)">BLUE</text>

      {/* Score overlay */}
      {_tick && (
        <text x={cx} y={ringT - 2} textAnchor="middle" fontSize={9} fill="rgba(255,255,255,0.7)">
          Round {_tick.period} · {_tick.home_score} – {_tick.away_score}
        </text>
      )}
    </svg>
  );
}
