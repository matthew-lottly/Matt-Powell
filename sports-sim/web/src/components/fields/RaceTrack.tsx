import type { StreamTick } from '../../types';

interface Props {
  tick: StreamTick | null;
}

/** Top-down SVG race track — oval circuit */
export default function RaceTrack({ tick: _tick }: Props) {
  const W = 440;
  const H = 240;
  const cx = W / 2;
  const cy = H / 2;
  const outerRx = 190;
  const outerRy = 90;
  const innerRx = 140;
  const innerRy = 50;

  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="w-full max-w-[560px]" aria-label="Race track">
      {/* Background */}
      <rect width={W} height={H} rx={6} fill="#2e7d32" />

      {/* Track surface */}
      <ellipse cx={cx} cy={cy} rx={outerRx} ry={outerRy} fill="#555" />
      <ellipse cx={cx} cy={cy} rx={innerRx} ry={innerRy} fill="#2e7d32" />

      {/* Track lines */}
      <ellipse cx={cx} cy={cy} rx={outerRx} ry={outerRy} fill="none" stroke="white" strokeWidth={2} />
      <ellipse cx={cx} cy={cy} rx={innerRx} ry={innerRy} fill="none" stroke="white" strokeWidth={1.5} />

      {/* Lane dividers */}
      {[0.25, 0.5, 0.75].map((t, i) => {
        const rx = innerRx + (outerRx - innerRx) * t;
        const ry = innerRy + (outerRy - innerRy) * t;
        return (
          <ellipse key={i} cx={cx} cy={cy} rx={rx} ry={ry}
            fill="none" stroke="white" strokeWidth={0.5} strokeDasharray="8 6" opacity={0.4} />
        );
      })}

      {/* Start/Finish line */}
      <line x1={cx} y1={cy - outerRy} x2={cx} y2={cy - innerRy}
        stroke="white" strokeWidth={3} />
      <rect x={cx - 12} y={cy - outerRy - 10} width={24} height={8}
        fill="none" stroke="white" strokeWidth={1} rx={1} />
      {/* Checkered pattern */}
      {[0, 1, 2, 3, 4, 5].map((i) => (
        <rect key={i} x={cx - 12 + i * 4} y={cy - outerRy - 10}
          width={4} height={4}
          fill={i % 2 === 0 ? 'white' : 'black'} />
      ))}
      {[0, 1, 2, 3, 4, 5].map((i) => (
        <rect key={`b${i}`} x={cx - 12 + i * 4} y={cy - outerRy - 6}
          width={4} height={4}
          fill={i % 2 === 0 ? 'black' : 'white'} />
      ))}

      {/* Pit lane (inside) */}
      <path
        d={`M ${cx - 80} ${cy + innerRy - 4} Q ${cx} ${cy + innerRy + 20} ${cx + 80} ${cy + innerRy - 4}`}
        fill="none" stroke="#f57c00" strokeWidth={1.5} strokeDasharray="6 3" />
      <text x={cx} y={cy + innerRy + 16} textAnchor="middle" fontSize={6} fill="#f57c00">PIT LANE</text>

      {/* Turn markers */}
      {[
        { x: cx - outerRx + 15, y: cy, label: 'T3' },
        { x: cx + outerRx - 15, y: cy, label: 'T1' },
        { x: cx, y: cy + outerRy - 8, label: 'T2' },
        { x: cx, y: cy - outerRy + 8, label: 'S/F' },
      ].map((t, i) => (
        <text key={i} x={t.x} y={t.y} textAnchor="middle" fontSize={7} fill="rgba(255,255,255,0.5)"
          dominantBaseline="middle">{t.label}</text>
      ))}

      {/* Lap/score overlay */}
      {_tick && (
        <text x={cx} y={cy} textAnchor="middle" fontSize={10} fill="rgba(255,255,255,0.5)"
          dominantBaseline="middle" fontWeight="bold">
          Lap {_tick.period}/50
        </text>
      )}
    </svg>
  );
}
