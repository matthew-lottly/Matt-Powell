import { useRef, useEffect } from 'react';
import type { SportType } from '../types';

interface EventItem {
  type: string;
  time: number;
  description: string;
  period: number;
}

interface Props {
  events: EventItem[];
  sport: SportType;
}

const EVENT_COLORS: Record<string, string> = {
  goal: 'text-green-400',
  home_run: 'text-green-400',
  three_pointer: 'text-green-400',
  hit: 'text-emerald-300',
  run: 'text-emerald-300',
  shot: 'text-blue-400',
  foul: 'text-yellow-400',
  injury: 'text-red-400',
  card: 'text-yellow-300',
  yellow_card: 'text-yellow-300',
  red_card: 'text-red-500',
  substitution: 'text-cyan-400',
  strikeout: 'text-orange-400',
  turnover: 'text-orange-400',
  steal: 'text-purple-400',
  block: 'text-purple-300',
  walk: 'text-gray-300',
  period_start: 'text-gray-500',
  period_end: 'text-gray-500',
  game_start: 'text-gray-500',
  game_end: 'text-green-400',
};

export default function EventLog({ events, sport: _sport }: Props) {
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [events.length]);

  return (
    <div className="bg-gray-900 border border-gray-800 rounded-xl p-4 flex flex-col max-h-[500px]">
      <h3 className="font-semibold text-gray-200 text-sm mb-2">Event Log</h3>
      <div className="flex-1 overflow-y-auto space-y-1 text-xs">
        {events.length === 0 && (
          <p className="text-gray-600 text-center py-8">No events yet</p>
        )}
        {events.map((ev, i) => (
          <div key={i} className="flex gap-2">
            <span className="text-gray-600 w-12 text-right shrink-0 tabular-nums">
              {ev.time.toFixed(1)}
            </span>
            <span className={EVENT_COLORS[ev.type] ?? 'text-gray-400'}>
              {ev.description}
            </span>
          </div>
        ))}
        <div ref={endRef} />
      </div>
    </div>
  );
}
