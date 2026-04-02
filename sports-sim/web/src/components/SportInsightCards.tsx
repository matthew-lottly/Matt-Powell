import { getSportPresentation } from '../sportPresentation';
import { getSportInsightCards } from '../sportUi';
import type { SportType, StreamTick } from '../types';

interface EventItem {
  type: string;
  time: number;
  description: string;
  period: number;
}

interface Props {
  sport: SportType;
  tick: StreamTick | null;
  events: EventItem[];
}

export default function SportInsightCards({ sport, tick, events }: Props) {
  const presentation = getSportPresentation(sport);
  const cards = getSportInsightCards(sport, tick, events);

  return (
    <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
      {cards.map((card) => (
        <div key={card.label} className="rounded-2xl border border-white/8 bg-slate-900/85 p-4 backdrop-blur-sm">
          <div className="text-[11px] uppercase tracking-[0.18em] text-slate-500">{card.label}</div>
          <div className={`mt-2 text-lg font-semibold ${presentation.accentText}`}>{card.value}</div>
          <div className="mt-1 text-xs text-slate-400">{card.detail}</div>
        </div>
      ))}
    </div>
  );
}