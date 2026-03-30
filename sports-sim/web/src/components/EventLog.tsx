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
