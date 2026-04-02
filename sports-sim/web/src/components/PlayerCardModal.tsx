import { useEffect, useRef } from 'react';

import type { PlayerCardData } from '../types';

interface Props {
  player: PlayerCardData | null;
  onClose: () => void;
}

const ATTR_LABELS: Record<string, string> = {
  speed: 'Speed',
  strength: 'Strength',
  skill: 'Skill',
  stamina_attr: 'Stamina',
  aggression: 'Aggression',
  decision_making: 'Decision',
  positioning: 'Positioning',
  teamwork: 'Teamwork',
};

function AttrBar({ label, value }: { label: string; value: number }) {
  const pct = Math.round(value * 100);
  const colorClass =
    pct >= 80 ? 'player-attr-fill-green' : pct >= 60 ? 'player-attr-fill-blue' : pct >= 40 ? 'player-attr-fill-yellow' : 'player-attr-fill-red';

  return (
    <div className="flex items-center gap-2 text-xs">
      <span className="app-copy-1 w-20 text-right">
        {label}
      </span>
      <progress className={`player-attr-progress ${colorClass}`} max={100} value={pct} />
      <span className="app-copy-0 w-8 text-right font-mono">
        {pct}
      </span>
    </div>
  );
}

export default function PlayerCardModal({ player, onClose }: Props) {
  const overlayRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!player) return;
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', handleKey);
    return () => window.removeEventListener('keydown', handleKey);
  }, [player, onClose]);

  if (!player) return null;

  const attrs = player.attributes ?? {};

  return (
    <div
      ref={overlayRef}
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60"
      onClick={(e) => {
        if (e.target === overlayRef.current) onClose();
      }}
      role="dialog"
      aria-modal="true"
      aria-label={`Player card: ${player.name}`}
    >
      <div
        className="app-surface-1 app-border-surface-2 rounded-xl border shadow-2xl p-5 w-80 max-h-[90vh] overflow-y-auto"
      >
        {/* Header */}
        <div className="flex items-start justify-between mb-4">
          <div>
            <h3 className="app-copy-0 text-lg font-bold">
              #{player.number} {player.name}
            </h3>
            <span
              className="app-surface-2 app-copy-1 text-xs font-mono px-2 py-0.5 rounded"
            >
              {player.position}
            </span>
            {player.age != null && (
              <span className="app-copy-1 ml-2 text-xs">
                Age {player.age}
              </span>
            )}
          </div>
          <button
            onClick={onClose}
            className="app-copy-1 text-lg px-2 hover:opacity-70"
            aria-label="Close player card"
          >
            &times;
          </button>
        </div>

        {/* Status */}
        {(player.stamina != null || player.morale != null || player.is_injured != null) && (
          <div className="app-copy-1 flex gap-3 text-xs mb-4">
            {player.stamina != null && <span>Stamina: {Math.round(player.stamina * 100)}%</span>}
            {player.morale != null && <span>Morale: {Math.round(player.morale * 100)}%</span>}
            {player.is_injured && (
              <span className="text-red-400 font-semibold">Injured</span>
            )}
            {player.minutes_played != null && <span>{player.minutes_played.toFixed(0)} min</span>}
          </div>
        )}

        {/* Attributes */}
        <div className="space-y-1.5">
          {Object.entries(attrs).map(([key, val]) => (
            <AttrBar key={key} label={ATTR_LABELS[key] ?? key} value={val} />
          ))}
        </div>
      </div>
    </div>
  );
}
