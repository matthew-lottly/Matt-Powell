import type { StreamTick } from '../../types';

interface Props {
  tick: StreamTick | null;
}

/** Top-down SVG MMA octagon */
export default function Octagon({ tick: _tick }: Props) {
  const W = 340;
  const H = 340;
  const cx = W / 2;
  const cy = H / 2;
  const R = 145;

  // Generate octagon points
  const points = Array.from({ length: 8 }, (_, i) => {
    const angle = (Math.PI / 8) + (i * Math.PI * 2) / 8;
    return `${cx + R * Math.cos(angle)},${cy + R * Math.sin(angle)}`;
  }).join(' ');

  const innerPoints = Array.from({ length: 8 }, (_, i) => {
    const angle = (Math.PI / 8) + (i * Math.PI * 2) / 8;
    const r = R * 0.88;
    return `${cx + r * Math.cos(angle)},${cy + r * Math.sin(angle)}`;
  }).join(' ');

  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="w-full max-w-[400px]" aria-label="MMA octagon">
      {/* Background */}
      <rect width={W} height={H} rx={6} fill="#1a1a2e" />

      {/* Octagon platform */}
      <polygon points={points} fill="#333" stroke="#555" strokeWidth={3} />

      {/* Canvas surface */}
      <polygon points={innerPoints} fill="#2a2a3a" stroke="rgba(255,255,255,0.15)" strokeWidth={1} />

      {/* UFC-style center logo area */}
      <circle cx={cx} cy={cy} r={35} fill="none" stroke="rgba(255,255,255,0.08)" strokeWidth={1} />
      <circle cx={cx} cy={cy} r={18} fill="none" stroke="rgba(255,255,255,0.05)" strokeWidth={1} />

      {/* Fence/cage lines */}
      {Array.from({ length: 8 }, (_, i) => {
        const angle1 = (Math.PI / 8) + (i * Math.PI * 2) / 8;
        const angle2 = (Math.PI / 8) + ((i + 1) * Math.PI * 2) / 8;
        const midAngle = (angle1 + angle2) / 2;
        // Vertical fence struts on each edge
        const x1 = cx + R * 0.94 * Math.cos(midAngle);
        const y1 = cy + R * 0.94 * Math.sin(midAngle);
        const x2 = cx + R * 0.72 * Math.cos(midAngle);
        const y2 = cy + R * 0.72 * Math.sin(midAngle);
        return <line key={i} x1={x1} y1={y1} x2={x2} y2={y2} stroke="rgba(255,255,255,0.06)" strokeWidth={0.5} />;
      })}

      {/* Corner posts */}
      {Array.from({ length: 8 }, (_, i) => {
        const angle = (Math.PI / 8) + (i * Math.PI * 2) / 8;
        const x = cx + R * Math.cos(angle);
        const y = cy + R * Math.sin(angle);
        return <circle key={i} cx={x} cy={y} r={4} fill="#dc143c" stroke="#333" strokeWidth={1} />;
      })}

      {/* Red/Blue corner indicators */}
      <text x={cx} y={cy - R + 22} textAnchor="middle" fontSize={7} fill="#ef5350" fontWeight="bold">RED</text>
      <text x={cx} y={cy + R - 14} textAnchor="middle" fontSize={7} fill="#42a5f5" fontWeight="bold">BLUE</text>

      {/* Score overlay */}
      {_tick && (
        <text x={cx} y={16} textAnchor="middle" fontSize={9} fill="rgba(255,255,255,0.6)">
          Round {_tick.period} · {_tick.home_score} – {_tick.away_score}
        </text>
      )}
    </svg>
  );
}
