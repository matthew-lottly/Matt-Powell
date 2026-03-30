import type { StreamTick } from '../../types';

interface Props {
  tick: StreamTick | null;
}

export default function FootballField({ tick: _tick }: Props) {
  const W = 600;
  const H = 260;
  const endZone = 50;
  const fieldLeft = endZone;
  const fieldRight = W - endZone;
  const fieldW = fieldRight - fieldLeft; // 500px for 100 yards

  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="w-full max-w-2xl" aria-label="Football field">
      {/* Grass */}
      <rect x="0" y="0" width={W} height={H} rx="8" fill="#2d5a27" />

      {/* End zones */}
      <rect x="0" y="0" width={endZone} height={H} fill="#1e3d6f" opacity="0.6" />
      <rect x={fieldRight} y="0" width={endZone} height={H} fill="#8b1a1a" opacity="0.6" />

      {/* End zone labels */}
      <text x={endZone / 2} y={H / 2} textAnchor="middle" dominantBaseline="middle"
        fill="white" fontSize="14" fontWeight="bold" opacity="0.5"
        transform={`rotate(-90, ${endZone / 2}, ${H / 2})`}>
        HOME
      </text>
      <text x={fieldRight + endZone / 2} y={H / 2} textAnchor="middle" dominantBaseline="middle"
        fill="white" fontSize="14" fontWeight="bold" opacity="0.5"
        transform={`rotate(90, ${fieldRight + endZone / 2}, ${H / 2})`}>
        AWAY
      </text>

      {/* Yard lines every 10 yards */}
      {Array.from({ length: 11 }, (_, i) => {
        const x = fieldLeft + (i * fieldW) / 10;
        return (
          <g key={i}>
            <line x1={x} y1={10} x2={x} y2={H - 10} stroke="white" strokeWidth="1" opacity="0.4" />
            {i > 0 && i < 10 && (
              <>
                <text x={x} y={22} textAnchor="middle" fill="white" fontSize="9" opacity="0.5">
                  {i <= 5 ? i * 10 : (10 - i) * 10}
                </text>
                <text x={x} y={H - 14} textAnchor="middle" fill="white" fontSize="9" opacity="0.5">
                  {i <= 5 ? i * 10 : (10 - i) * 10}
                </text>
              </>
            )}
          </g>
        );
      })}

      {/* Hash marks every 5 yards */}
      {Array.from({ length: 21 }, (_, i) => {
        if (i % 2 === 0) return null;
        const x = fieldLeft + (i * fieldW) / 20;
        return (
          <g key={`h${i}`}>
            <line x1={x} y1={10} x2={x} y2={H - 10} stroke="white" strokeWidth="0.5" opacity="0.2" />
          </g>
        );
      })}

      {/* 50-yard line (midfield) highlight */}
      <line x1={fieldLeft + fieldW / 2} y1={10} x2={fieldLeft + fieldW / 2} y2={H - 10}
        stroke="white" strokeWidth="2" opacity="0.6" />

      {/* Field border */}
      <rect x={fieldLeft} y="10" width={fieldW} height={H - 20}
        fill="none" stroke="white" strokeWidth="2" opacity="0.6" />

      {/* Sidelines */}
      <line x1="0" y1="10" x2={W} y2="10" stroke="white" strokeWidth="1" opacity="0.3" />
      <line x1="0" y1={H - 10} x2={W} y2={H - 10} stroke="white" strokeWidth="1" opacity="0.3" />
    </svg>
  );
}
