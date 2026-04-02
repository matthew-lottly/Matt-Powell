import { useMemo } from 'react';
import type { SportType, StreamTick } from '../types';
import { getSportPresentation } from '../sportPresentation';

interface Props {
  sport: SportType;
  ticks: StreamTick[];
}

interface StatRow {
  label: string;
  home: string | number;
  away: string | number;
}

export default function PostGameSummary({ sport, ticks }: Props) {
  const presentation = getSportPresentation(sport);
  const lastTick = ticks[ticks.length - 1];
  if (!lastTick || !lastTick.is_finished) return null;

  const allEvents = ticks.flatMap((t) => t.events);
  const ss = lastTick.sport_state ?? {};

  const stats = useMemo((): StatRow[] => {
    const rows: StatRow[] = [
      { label: 'Final Score', home: lastTick.home_score, away: lastTick.away_score },
    ];

    if (sport === 'soccer') {
      rows.push(
        { label: 'Shots', home: (ss.home_shots as number) ?? 0, away: (ss.away_shots as number) ?? 0 },
        { label: 'Corners', home: (ss.home_corners as number) ?? 0, away: (ss.away_corners as number) ?? 0 },
        { label: 'Fouls', home: (ss.home_fouls as number) ?? 0, away: (ss.away_fouls as number) ?? 0 },
        { label: 'Yellow Cards', home: (ss.home_yellows as number) ?? 0, away: (ss.away_yellows as number) ?? 0 },
        { label: 'Red Cards', home: (ss.home_reds as number) ?? 0, away: (ss.away_reds as number) ?? 0 },
      );
    } else if (sport === 'basketball') {
      rows.push(
        { label: 'FG Attempts', home: (ss.home_fg_att as number) ?? 0, away: (ss.away_fg_att as number) ?? 0 },
        { label: '3-Pointers', home: (ss.home_3pt as number) ?? 0, away: (ss.away_3pt as number) ?? 0 },
        { label: 'Free Throws', home: (ss.home_ft as number) ?? 0, away: (ss.away_ft as number) ?? 0 },
        { label: 'Rebounds', home: (ss.home_rebounds as number) ?? 0, away: (ss.away_rebounds as number) ?? 0 },
        { label: 'Turnovers', home: (ss.home_turnovers as number) ?? 0, away: (ss.away_turnovers as number) ?? 0 },
      );
    } else if (sport === 'baseball') {
      rows.push(
        { label: 'Hits', home: (ss.home_hits as number) ?? 0, away: (ss.away_hits as number) ?? 0 },
        { label: 'Strikeouts', home: (ss.home_strikeouts as number) ?? 0, away: (ss.away_strikeouts as number) ?? 0 },
        { label: 'Errors', home: (ss.home_errors as number) ?? 0, away: (ss.away_errors as number) ?? 0 },
      );
    } else if (sport === 'football') {
      rows.push(
        { label: 'Total Yards', home: (ss.home_total_yards as number) ?? 0, away: (ss.away_total_yards as number) ?? 0 },
        { label: 'Turnovers', home: (ss.home_turnovers as number) ?? 0, away: (ss.away_turnovers as number) ?? 0 },
        { label: 'Sacks', home: (ss.home_sacks as number) ?? 0, away: (ss.away_sacks as number) ?? 0 },
        { label: 'Penalties', home: (ss.home_penalties as number) ?? 0, away: (ss.away_penalties as number) ?? 0 },
      );
    } else if (sport === 'hockey') {
      rows.push(
        { label: 'Shots', home: (ss.home_shots as number) ?? 0, away: (ss.away_shots as number) ?? 0 },
        { label: 'Saves', home: (ss.home_saves as number) ?? 0, away: (ss.away_saves as number) ?? 0 },
        { label: 'Faceoff Wins', home: (ss.home_faceoff_wins as number) ?? 0, away: (ss.away_faceoff_wins as number) ?? 0 },
        { label: 'Penalties', home: (ss.home_penalties as number) ?? 0, away: (ss.away_penalties as number) ?? 0 },
      );
    } else if (sport === 'tennis') {
      rows.push(
        { label: 'Sets', home: (ss.p1_sets as number) ?? 0, away: (ss.p2_sets as number) ?? 0 },
        { label: 'Games', home: (ss.p1_games as number) ?? 0, away: (ss.p2_games as number) ?? 0 },
        { label: 'Aces', home: (ss.p1_aces as number) ?? 0, away: (ss.p2_aces as number) ?? 0 },
        { label: 'Winners', home: (ss.p1_winners as number) ?? 0, away: (ss.p2_winners as number) ?? 0 },
        { label: 'Unforced Errors', home: (ss.p1_unforced_errors as number) ?? 0, away: (ss.p2_unforced_errors as number) ?? 0 },
      );
    } else if (sport === 'golf') {
      const fmtPar = (n: number) => n === 0 ? 'E' : n > 0 ? `+${n}` : `${n}`;
      rows.push(
        { label: 'Total Strokes', home: (ss.p1_total_strokes as number) ?? 0, away: (ss.p2_total_strokes as number) ?? 0 },
        { label: 'Relative to Par', home: fmtPar((ss.p1_relative_to_par as number) ?? 0), away: fmtPar((ss.p2_relative_to_par as number) ?? 0) },
        { label: 'Birdies', home: (ss.p1_birdies as number) ?? 0, away: (ss.p2_birdies as number) ?? 0 },
      );
    } else if (sport === 'cricket') {
      rows.push(
        { label: 'Wickets', home: (ss.wickets as number) ?? 0, away: '-' },
        { label: 'Overs', home: (ss.over_display as string) ?? '0.0', away: '-' },
        { label: 'Fours', home: (ss.boundaries_four as number) ?? 0, away: '-' },
        { label: 'Sixes', home: (ss.sixes as number) ?? 0, away: '-' },
      );
    } else if (sport === 'boxing' || sport === 'mma') {
      rows.push(
        { label: 'Health', home: `${Math.round((ss.p1_health as number) ?? 100)}%`, away: `${Math.round((ss.p2_health as number) ?? 100)}%` },
        { label: 'Scorecard Total', home: (ss.p1_total_score as number) ?? 0, away: (ss.p2_total_score as number) ?? 0 },
      );
      if (sport === 'boxing') {
        rows.push(
          { label: 'Knockdowns', home: (ss.p1_knockdowns as number) ?? 0, away: (ss.p2_knockdowns as number) ?? 0 },
          { label: 'Punches', home: (ss.p1_punches as number) ?? 0, away: (ss.p2_punches as number) ?? 0 },
        );
      } else {
        rows.push(
          { label: 'Strikes', home: (ss.p1_strikes as number) ?? 0, away: (ss.p2_strikes as number) ?? 0 },
          { label: 'Takedowns', home: (ss.p1_takedowns as number) ?? 0, away: (ss.p2_takedowns as number) ?? 0 },
        );
      }
    } else if (sport === 'racing') {
      rows.push(
        { label: 'Laps', home: (ss.p1_lap as number) ?? 0, away: (ss.p2_lap as number) ?? 0 },
        { label: 'Pit Stops', home: (ss.p1_pit_stops as number) ?? 0, away: (ss.p2_pit_stops as number) ?? 0 },
        { label: 'Status', home: (ss.p1_dnf as boolean) ? 'DNF' : 'Finished', away: (ss.p2_dnf as boolean) ? 'DNF' : 'Finished' },
      );
    }

    return rows;
  }, [lastTick, sport, ss, allEvents]);

  const winner = lastTick.home_score > lastTick.away_score ? lastTick.home_team
    : lastTick.away_score > lastTick.home_score ? lastTick.away_team
    : null;

  return (
    <section aria-label="Post-game summary" className="rounded-2xl border border-white/8 bg-slate-900/85 p-5 backdrop-blur-sm">
      <div className="flex items-center justify-between mb-4">
        <h3 className={`text-lg font-bold ${presentation.accentText}`}>
          {winner ? `${winner} Wins!` : 'Draw'}
        </h3>
        <span className="text-xs text-slate-500 uppercase tracking-widest" role="status">Final</span>
      </div>
      <table className="w-full text-sm">
        <caption className="sr-only">Post-game statistics</caption>
        <thead>
          <tr className="text-xs text-slate-500 uppercase tracking-wider border-b border-white/5">
            <th scope="col" className="text-left py-1.5 font-medium">Stat</th>
            <th scope="col" className="text-center py-1.5 font-medium">{lastTick.home_team}</th>
            <th scope="col" className="text-center py-1.5 font-medium">{lastTick.away_team}</th>
          </tr>
        </thead>
        <tbody>
          {stats.map((row) => (
            <tr key={row.label} className="border-b border-white/5 hover:bg-white/5 transition-colors">
              <td className="py-1.5 text-slate-400">{row.label}</td>
              <td className="text-center text-slate-200 tabular-nums font-medium">{row.home}</td>
              <td className="text-center text-slate-200 tabular-nums font-medium">{row.away}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <div className="mt-3 text-xs text-slate-500">
        Total events: {allEvents.length} · Periods: {lastTick.period}
      </div>
    </section>
  );
}
