import type { StreamTick } from '../../types';

interface Props {
  tick: StreamTick | null;
}

/** Top-down SVG baseball diamond + outfield */
export default function BaseballDiamond({ tick: _tick }: Props) {
  const W = 400;
  const H = 380;

  // Diamond points (home plate at bottom-center)
  const home = [W / 2, H - 50];
  const first = [W / 2 + 80, H - 130];
  const second = [W / 2, H - 210];
  const third = [W / 2 - 80, H - 130];

  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="w-full max-w-[460px]" aria-label="Baseball diamond">
      {/* Outfield grass */}
      <path
        d={`M 20,${H - 30} Q ${W / 2},10 ${W - 20},${H - 30} Z`}
        className="fill-field-baseball"
        opacity={0.8}
      />

      {/* Infield dirt */}
      <polygon
        points={`${home[0]},${home[1]} ${first[0]},${first[1]} ${second[0]},${second[1]} ${third[0]},${third[1]}`}
        fill="#c4a46e"
        opacity={0.7}
      />

      {/* Base lines */}
      <polygon
        points={`${home[0]},${home[1]} ${first[0]},${first[1]} ${second[0]},${second[1]} ${third[0]},${third[1]}`}
        fill="none"
        stroke="white"
        strokeWidth={1.2}
      />

      {/* Foul lines */}
      <line x1={home[0]!} y1={home[1]!} x2={20} y2={30} stroke="white" strokeWidth={0.8} opacity={0.5} />
      <line x1={home[0]!} y1={home[1]!} x2={W - 20} y2={30} stroke="white" strokeWidth={0.8} opacity={0.5} />

      {/* Bases */}
      {[home, first, second, third].map(([x, y], i) => (
        <rect
          key={i}
          x={x! - 5}
          y={y! - 5}
          width={10}
          height={10}
          fill="white"
          transform={`rotate(45, ${x}, ${y})`}
        />
      ))}

      {/* Pitcher's mound */}
      <circle cx={W / 2} cy={(home[1]! + second[1]!) / 2} r={8} fill="#c4a46e" stroke="white" strokeWidth={0.8} />
      <rect cx={W / 2} cy={(home[1]! + second[1]!) / 2} x={W / 2 - 3} y={(home[1]! + second[1]!) / 2 - 1} width={6} height={2} fill="white" />

      {/* Base labels */}
      <text x={home[0]!} y={home[1]! + 18} textAnchor="middle" fontSize={8} fill="white" opacity={0.6}>
        HOME
      </text>
      <text x={first[0]! + 14} y={first[1]! + 4} fontSize={7} fill="white" opacity={0.5}>
        1B
      </text>
      <text x={second[0]!} y={second[1]! - 10} textAnchor="middle" fontSize={7} fill="white" opacity={0.5}>
        2B
      </text>
      <text x={third[0]! - 18} y={third[1]! + 4} fontSize={7} fill="white" opacity={0.5}>
        3B
      </text>

      {/* Score overlay */}
      {_tick && (
        <text x={W / 2} y={18} textAnchor="middle" fontSize={9} fill="rgba(255,255,255,0.5)">
          {_tick.home_score} – {_tick.away_score}
        </text>
      )}
    </svg>
  );
}
