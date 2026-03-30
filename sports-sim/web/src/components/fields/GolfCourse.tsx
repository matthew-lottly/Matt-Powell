import type { StreamTick } from '../../types';

interface Props {
  tick: StreamTick | null;
}

/** Overhead SVG golf hole layout */
export default function GolfCourse({ tick: _tick }: Props) {
  const W = 400;
  const H = 200;

  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="w-full max-w-[560px]" aria-label="Golf course">
      {/* Sky */}
      <rect width={W} height={H} rx={6} fill="#87ceeb" />

      {/* Fairway */}
      <ellipse cx={W / 2} cy={H / 2 + 10} rx={160} ry={60} fill="#228b22" />

      {/* Rough edges */}
      <ellipse cx={W / 2} cy={H / 2 + 10} rx={180} ry={75} fill="none" stroke="#1a6b1a" strokeWidth={8} opacity={0.4} />

      {/* Fairway stripe pattern */}
      {[-80, -40, 0, 40, 80].map((offset, i) => (
        <ellipse key={i} cx={W / 2 + offset * 0.3} cy={H / 2 + 10}
          rx={8} ry={55} fill={i % 2 === 0 ? '#1e8c1e' : '#2da02d'} opacity={0.3} />
      ))}

      {/* Tee box */}
      <rect x={40} y={H / 2 - 8} width={20} height={16} rx={3} fill="#2e7d32" stroke="#1b5e20" strokeWidth={1} />
      <circle cx={50} cy={H / 2} r={2} fill="white" />

      {/* Sand bunkers */}
      <ellipse cx={280} cy={H / 2 - 25} rx={14} ry={8} fill="#f5deb3" stroke="#d4a574" strokeWidth={0.8} />
      <ellipse cx={310} cy={H / 2 + 30} rx={12} ry={6} fill="#f5deb3" stroke="#d4a574" strokeWidth={0.8} />

      {/* Water hazard */}
      <ellipse cx={250} cy={H / 2 + 35} rx={18} ry={10} fill="#4fc3f7" stroke="#0288d1" strokeWidth={0.8} opacity={0.7} />

      {/* Green */}
      <ellipse cx={340} cy={H / 2} rx={30} ry={24} fill="#00c853" stroke="#00a844" strokeWidth={1} />

      {/* Pin/flag */}
      <line x1={345} y1={H / 2 - 20} x2={345} y2={H / 2} stroke="#555" strokeWidth={1} />
      <polygon points={`345,${H / 2 - 20} 358,${H / 2 - 15} 345,${H / 2 - 10}`} fill="#e53935" />
      <circle cx={345} cy={H / 2} r={2} fill="#333" />

      {/* Hole info */}
      {_tick && (
        <text x={W / 2} y={18} textAnchor="middle" fontSize={9} fill="rgba(0,0,0,0.5)" fontWeight="bold">
          Hole {_tick.period} · {_tick.home_score} / {_tick.away_score}
        </text>
      )}
    </svg>
  );
}
