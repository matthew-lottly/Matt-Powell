import type { StreamTick } from '../../types';

interface Props {
  tick: StreamTick | null;
}

/** Top-down SVG tennis court — singles 23.77 × 8.23 m */
export default function TennisCourt({ tick: _tick }: Props) {
  const W = 380;
  const H = 200;
  const cx = W / 2;
  const cy = H / 2;

  // Court boundaries
  const courtL = 30;
  const courtR = W - 30;
  const courtT = 20;
  const courtB = H - 20;
  const courtW = courtR - courtL;
  const courtH = courtB - courtT;

  // Service box dimensions
  const serviceDepth = courtH * 0.38;

  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="w-full max-w-[560px]" aria-label="Tennis court">
      {/* Court surface */}
      <rect width={W} height={H} rx={6} fill="#2563eb" />

      {/* Playing surface (hard court blue) */}
      <rect x={courtL} y={courtT} width={courtW} height={courtH} fill="#1d4ed8" stroke="white" strokeWidth={2} />

      {/* Net (center line) */}
      <line x1={cx} y1={courtT - 4} x2={cx} y2={courtB + 4} stroke="white" strokeWidth={2.5} />

      {/* Center service line */}
      <line x1={cx - courtW * 0.38} y1={cy} x2={cx + courtW * 0.38} y2={cy} stroke="white" strokeWidth={1} />

      {/* Service boxes - left side */}
      <rect x={cx - courtW * 0.38} y={courtT} width={courtW * 0.38} height={serviceDepth}
        fill="none" stroke="white" strokeWidth={1} />
      <rect x={cx - courtW * 0.38} y={courtB - serviceDepth} width={courtW * 0.38} height={serviceDepth}
        fill="none" stroke="white" strokeWidth={1} />

      {/* Service boxes - right side */}
      <rect x={cx} y={courtT} width={courtW * 0.38} height={serviceDepth}
        fill="none" stroke="white" strokeWidth={1} />
      <rect x={cx} y={courtB - serviceDepth} width={courtW * 0.38} height={serviceDepth}
        fill="none" stroke="white" strokeWidth={1} />

      {/* Baseline center marks */}
      <line x1={courtL} y1={cy} x2={courtL + 6} y2={cy} stroke="white" strokeWidth={1} />
      <line x1={courtR} y1={cy} x2={courtR - 6} y2={cy} stroke="white" strokeWidth={1} />

      {/* Doubles lines (slightly wider) */}
      <line x1={courtL - 8} y1={courtT} x2={courtL - 8} y2={courtB} stroke="white" strokeWidth={0.5} strokeDasharray="4 3" />
      <line x1={courtR + 8} y1={courtT} x2={courtR + 8} y2={courtB} stroke="white" strokeWidth={0.5} strokeDasharray="4 3" />

      {/* Score overlay */}
      {_tick && (
        <text x={cx} y={14} textAnchor="middle" fontSize={8} fill="rgba(255,255,255,0.5)">
          {_tick.home_score} – {_tick.away_score}
        </text>
      )}
    </svg>
  );
}
