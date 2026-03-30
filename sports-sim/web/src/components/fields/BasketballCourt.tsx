import type { StreamTick } from '../../types';

interface Props {
  tick: StreamTick | null;
}

/** Top-down SVG basketball half-court / full court */
export default function BasketballCourt({ tick: _tick }: Props) {
  const W = 420;
  const H = 220;

  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="w-full max-w-[560px]" aria-label="Basketball court">
      {/* Floor */}
      <rect width={W} height={H} rx={6} className="fill-field-basketball" />

      {/* Outline */}
      <rect x={10} y={10} width={W - 20} height={H - 20} fill="none" stroke="white" strokeWidth={1.5} rx={2} />

      {/* Center line */}
      <line x1={W / 2} y1={10} x2={W / 2} y2={H - 10} stroke="white" strokeWidth={1} />

      {/* Center circle */}
      <circle cx={W / 2} cy={H / 2} r={24} fill="none" stroke="white" strokeWidth={1} />

      {/* Left key (paint) */}
      <rect x={10} y={H / 2 - 40} width={76} height={80} fill="none" stroke="white" strokeWidth={1} />
      <circle cx={86} cy={H / 2} r={24} fill="none" stroke="white" strokeWidth={1} />

      {/* Left basket */}
      <circle cx={24} cy={H / 2} r={4} fill="none" stroke="white" strokeWidth={1.2} />
      <rect x={10} y={H / 2 - 4} width={14} height={1} fill="white" />

      {/* Left three-point arc */}
      <path
        d={`M 10,${H / 2 - 70} L 30,${H / 2 - 70} A 90,90 0 0,1 30,${H / 2 + 70} L 10,${H / 2 + 70}`}
        fill="none"
        stroke="white"
        strokeWidth={0.8}
      />

      {/* Right key mirror */}
      <rect x={W - 86} y={H / 2 - 40} width={76} height={80} fill="none" stroke="white" strokeWidth={1} />
      <circle cx={W - 86} cy={H / 2} r={24} fill="none" stroke="white" strokeWidth={1} />

      {/* Right basket */}
      <circle cx={W - 24} cy={H / 2} r={4} fill="none" stroke="white" strokeWidth={1.2} />
      <rect x={W - 24} y={H / 2 - 4} width={14} height={1} fill="white" />

      {/* Right three-point arc */}
      <path
        d={`M ${W - 10},${H / 2 - 70} L ${W - 30},${H / 2 - 70} A 90,90 0 0,0 ${W - 30},${H / 2 + 70} L ${W - 10},${H / 2 + 70}`}
        fill="none"
        stroke="white"
        strokeWidth={0.8}
      />

      {/* Score overlay */}
      {_tick && (
        <text x={W / 2} y={18} textAnchor="middle" fontSize={8} fill="rgba(255,255,255,0.5)">
          {_tick.home_score} – {_tick.away_score}
        </text>
      )}
    </svg>
  );
}
