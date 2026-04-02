import { useRef, useEffect, useState, useMemo } from 'react';
import type { SportType } from '../types';
import { getSportPresentation } from '../sportPresentation';
import { formatSportClock, formatSportPeriod } from '../sportUi';

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

/** Event categories for the filter buttons */
const EVENT_CATEGORIES: Record<string, string[]> = {
  Scoring: ['goal', 'touchdown', 'field_goal', 'home_run', 'run', 'three_pointer', 'free_throw', 'extra_point', 'two_point_conversion', 'safety', 'birdie', 'eagle', 'ace', 'set_won', 'six', 'boundary_four', 'knockout', 'tko', 'checkered_flag'],
  Shots: ['shot', 'save', 'tee_shot', 'putt', 'punch', 'ground_strike'],
  Turnovers: ['turnover', 'interception', 'fumble', 'steal', 'strikeout', 'wicket', 'double_fault', 'unforced_error'],
  Discipline: ['foul', 'yellow_card', 'red_card', 'penalty_flag', 'penalty_minutes', 'wide', 'no_ball'],
  Momentum: ['substitution', 'power_play', 'break_point', 'match_point', 'overtake', 'pit_stop', 'takedown', 'knockdown'],
};

const EVENT_COLORS: Record<string, string> = {
  // Universal
  goal: 'text-green-400',
  home_run: 'text-green-400',
  three_pointer: 'text-green-400',
  touchdown: 'text-green-400',
  field_goal: 'text-green-300',
  safety: 'text-green-300',
  extra_point: 'text-green-200',
  two_point_conversion: 'text-green-400',
  hit: 'text-emerald-300',
  run: 'text-emerald-300',
  rush: 'text-emerald-300',
  reception: 'text-emerald-300',
  shot: 'text-blue-400',
  foul: 'text-yellow-400',
  penalty_flag: 'text-yellow-400',
  injury: 'text-red-400',
  card: 'text-yellow-300',
  yellow_card: 'text-yellow-300',
  red_card: 'text-red-500',
  substitution: 'text-cyan-400',
  strikeout: 'text-orange-400',
  turnover: 'text-orange-400',
  interception: 'text-orange-400',
  fumble: 'text-orange-400',
  sack: 'text-purple-400',
  steal: 'text-purple-400',
  block: 'text-purple-300',
  walk: 'text-gray-300',
  punt: 'text-gray-400',
  kickoff: 'text-gray-400',
  incomplete_pass: 'text-gray-400',
  period_start: 'text-gray-500',
  period_end: 'text-gray-500',
  game_start: 'text-gray-500',
  game_end: 'text-green-400',
  // Hockey
  power_play: 'text-yellow-400',
  penalty_minutes: 'text-yellow-300',
  face_off: 'text-blue-300',
  icing: 'text-cyan-300',
  save: 'text-blue-400',
  hat_trick: 'text-green-500',
  empty_net: 'text-green-300',
  // Tennis
  ace: 'text-green-400',
  double_fault: 'text-red-400',
  winner: 'text-green-300',
  unforced_error: 'text-orange-400',
  break_point: 'text-yellow-400',
  set_won: 'text-green-500',
  match_point: 'text-green-400',
  serve: 'text-blue-300',
  return: 'text-blue-300',
  volley: 'text-emerald-300',
  // Golf
  tee_shot: 'text-blue-300',
  fairway_hit: 'text-emerald-300',
  green_in_regulation: 'text-green-300',
  putt: 'text-blue-300',
  birdie: 'text-green-400',
  eagle: 'text-green-500',
  bogey: 'text-red-400',
  par: 'text-gray-300',
  hole_complete: 'text-gray-400',
  // Cricket
  wicket: 'text-red-400',
  boundary_four: 'text-green-400',
  six: 'text-green-500',
  over_complete: 'text-gray-400',
  maiden_over: 'text-blue-400',
  lbw: 'text-red-400',
  caught: 'text-orange-400',
  bowled: 'text-red-500',
  run_out: 'text-orange-400',
  wide: 'text-yellow-300',
  no_ball: 'text-yellow-400',
  // Boxing / MMA
  punch: 'text-orange-300',
  knockout: 'text-red-500',
  tko: 'text-red-500',
  decision: 'text-blue-300',
  round_end: 'text-gray-400',
  knockdown: 'text-red-400',
  clinch: 'text-yellow-300',
  submission: 'text-purple-400',
  takedown: 'text-blue-400',
  ground_strike: 'text-orange-400',
  split_decision: 'text-blue-300',
  // Racing
  lap_complete: 'text-gray-400',
  pit_stop: 'text-yellow-400',
  overtake: 'text-green-400',
  crash: 'text-red-500',
  yellow_flag: 'text-yellow-400',
  checkered_flag: 'text-green-500',
  dnf: 'text-red-400',
  fastest_lap: 'text-purple-400',
};

export default function EventLog({ events, sport }: Props) {
  const endRef = useRef<HTMLDivElement>(null);
  const presentation = getSportPresentation(sport);
  const [filter, setFilter] = useState<string | null>(null);

  const filtered = useMemo(() => {
    if (!filter) return events;
    const types = EVENT_CATEGORIES[filter] ?? [];
    return events.filter((e) => types.includes(e.type));
  }, [events, filter]);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [filtered.length]);

  return (
    <section aria-labelledby="event-log-heading" className="bg-slate-900/90 border border-white/8 rounded-2xl p-4 flex flex-col max-h-[500px] backdrop-blur-sm">
      <div className="mb-3">
        <h3 id="event-log-heading" className="font-semibold text-slate-100 text-sm">{presentation.label} Event Log</h3>
        <p className="mt-1 text-xs text-slate-500">Tracking {presentation.rhythm} in real time.</p>
      </div>
      {/* Filter buttons */}
      <div className="flex flex-wrap gap-1 mb-2">
        <button
          type="button"
          onClick={() => setFilter(null)}
          className={`px-2 py-0.5 rounded-full text-[10px] uppercase tracking-wider transition ${!filter ? 'bg-white/15 text-white' : 'bg-white/5 text-slate-400 hover:bg-white/10'}`}
        >
          All ({events.length})
        </button>
        {Object.keys(EVENT_CATEGORIES).map((cat) => {
          const count = events.filter((e) => (EVENT_CATEGORIES[cat] ?? []).includes(e.type)).length;
          if (count === 0) return null;
          return (
            <button
              type="button"
              key={cat}
              onClick={() => setFilter(filter === cat ? null : cat)}
              className={`px-2 py-0.5 rounded-full text-[10px] uppercase tracking-wider transition ${filter === cat ? 'bg-white/15 text-white' : 'bg-white/5 text-slate-400 hover:bg-white/10'}`}
            >
              {cat} ({count})
            </button>
          );
        })}
      </div>
      <div role="log" aria-live="polite" className="flex-1 overflow-y-auto space-y-1 text-xs">
        {filtered.length === 0 && (
          <p className="text-slate-500 text-center py-8">{filter ? `No ${filter.toLowerCase()} events yet` : presentation.emptyState}</p>
        )}
        {filtered.map((ev, i) => (
          <div key={i} className="flex gap-2 rounded-xl px-2 py-1.5 hover:bg-white/5 transition-colors">
            <div className="w-20 shrink-0 text-right">
              <div className="text-[10px] uppercase tracking-[0.14em] text-slate-600">{formatSportPeriod(sport, ev.period)}</div>
              <div className="text-[11px] tabular-nums text-slate-500">{formatSportClock(sport, ev.time)}</div>
            </div>
            <span className={EVENT_COLORS[ev.type] ?? 'text-gray-400'}>
              {ev.description}
            </span>
          </div>
        ))}
        <div ref={endRef} />
      </div>
    </section>
  );
}
