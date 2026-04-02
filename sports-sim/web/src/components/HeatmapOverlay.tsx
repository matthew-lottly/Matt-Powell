import { useEffect, useState } from 'react';

interface HeatBin {
  x: number;
  y: number;
  count: number;
  success_count: number;
}

interface Props {
  gameId: string | null;
  width?: number;
  height?: number;
  team?: 'home' | 'away' | null;
  eventType?: string | null;
}

const CELL_W = 10;
const CELL_H = 10;

function intensityColor(ratio: number): string {
  // ratio 0‒1 mapped to blue→yellow→red
  if (ratio < 0.33) {
    const t = ratio / 0.33;
    return `rgba(59, 130, 246, ${0.15 + t * 0.35})`;  // blue
  }
  if (ratio < 0.66) {
    const t = (ratio - 0.33) / 0.33;
    return `rgba(234, 179, 8, ${0.3 + t * 0.4})`;      // yellow
  }
  const t = (ratio - 0.66) / 0.34;
  return `rgba(239, 68, 68, ${0.4 + t * 0.45})`;        // red
}

export default function HeatmapOverlay({ gameId, width = 100, height = 100, team, eventType }: Props) {
  const [bins, setBins] = useState<HeatBin[]>([]);
  const [maxCount, setMaxCount] = useState(1);

  useEffect(() => {
    if (!gameId) return;

    const params = new URLSearchParams();
    if (team) params.set('team', team);
    if (eventType) params.set('event_type', eventType);
    const qs = params.toString();

    fetch(`/api/simulations/${gameId}/heatmap${qs ? '?' + qs : ''}`)
      .then((r) => r.json())
      .then((data: { bins: HeatBin[] }) => {
        setBins(data.bins);
        const m = Math.max(1, ...data.bins.map((b) => b.count));
        setMaxCount(m);
      })
      .catch(() => setBins([]));
  }, [gameId, team, eventType]);

  if (bins.length === 0) return null;

  return (
    <svg
      viewBox={`0 0 ${width} ${height}`}
      className="absolute inset-0 w-full h-full pointer-events-none"
      role="img"
      aria-label="Heatmap overlay showing event density across the field"
    >
      {bins.map((b) => {
        const ratio = b.count / maxCount;
        return (
          <rect
            key={`${b.x}-${b.y}`}
            x={b.x - CELL_W / 2}
            y={b.y - CELL_H / 2}
            width={CELL_W}
            height={CELL_H}
            fill={intensityColor(ratio)}
            rx={1}
          />
        );
      })}
    </svg>
  );
}
