import type { StreamTick } from '../../types';

interface Props {
  tick: StreamTick | null;
}

/** Top-down SVG hockey rink — 200 × 85 ft scaled */
export default function HockeyRink({ tick: _tick }: Props) {
  const W = 400;
  const H = 170;
  const cx = W / 2;
  const cy = H / 2;

  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="w-full max-w-[560px]" aria-label="Hockey rink">
      {/* Ice surface */}
      <rect width={W} height={H} rx={40} className="fill-sky-100" />

      {/* Rink outline */}
      <rect x={4} y={4} width={W - 8} height={H - 8} rx={38} fill="none" stroke="#333" strokeWidth={2} />

      {/* Center red line */}
      <line x1={cx} y1={4} x2={cx} y2={H - 4} stroke="#d32f2f" strokeWidth={2.5} />

      {/* Center circle */}
      <circle cx={cx} cy={cy} r={24} fill="none" stroke="#1565c0" strokeWidth={1.5} />
      <circle cx={cx} cy={cy} r={2} fill="#1565c0" />

      {/* Blue lines */}
      <line x1={cx - 60} y1={4} x2={cx - 60} y2={H - 4} stroke="#1565c0" strokeWidth={2} />
      <line x1={cx + 60} y1={4} x2={cx + 60} y2={H - 4} stroke="#1565c0" strokeWidth={2} />

      {/* Goal creases */}
      <rect x={16} y={cy - 10} width={6} height={20} rx={1} fill="none" stroke="#d32f2f" strokeWidth={1} />
      <path d={`M 22 ${cy - 14} A 18 18 0 0 1 22 ${cy + 14}`} fill="rgba(173,216,230,0.4)" stroke="#1565c0" strokeWidth={0.8} />

      <rect x={W - 22} y={cy - 10} width={6} height={20} rx={1} fill="none" stroke="#d32f2f" strokeWidth={1} />
      <path d={`M ${W - 22} ${cy - 14} A 18 18 0 0 0 ${W - 22} ${cy + 14}`} fill="rgba(173,216,230,0.4)" stroke="#1565c0" strokeWidth={0.8} />

      {/* Face-off circles (offensive zones) */}
      {[cx - 110, cx + 110].map((fx) =>
        [cy - 30, cy + 30].map((fy, j) => (
          <g key={`${fx}-${j}`}>
            <circle cx={fx} cy={fy} r={18} fill="none" stroke="#d32f2f" strokeWidth={0.8} />
            <circle cx={fx} cy={fy} r={2} fill="#d32f2f" />
          </g>
        )),
      )}

      {/* Neutral zone face-off dots */}
      {[cx - 60, cx + 60].map((fx) =>
        [cy - 30, cy + 30].map((fy, j) => (
          <circle key={`nz-${fx}-${j}`} cx={fx} cy={fy} r={2} fill="#d32f2f" />
        )),
      )}

      {/* Goal lines */}
      <line x1={34} y1={10} x2={34} y2={H - 10} stroke="#d32f2f" strokeWidth={1} />
      <line x1={W - 34} y1={10} x2={W - 34} y2={H - 10} stroke="#d32f2f" strokeWidth={1} />

      {/* Score overlay */}
      {_tick && (
        <text x={cx} y={14} textAnchor="middle" fontSize={8} fill="rgba(0,0,0,0.4)">
          {_tick.home_score} – {_tick.away_score}
        </text>
      )}
    </svg>
  );
}
