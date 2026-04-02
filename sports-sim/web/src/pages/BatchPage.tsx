import { useState } from 'react';
import { fetchSports, fetchTeams, fetchLeagues, batchSimulate } from '../api';
import { useEffect } from 'react';
import type { LeagueOption, TeamOption } from '../types';

interface BatchResult {
  game_id: string;
  home_score: number;
  away_score: number;
  winner: string;
}

export default function BatchPage() {
  const [sports, setSports] = useState<string[]>([]);
  const [sport, setSport] = useState('soccer');
  const [leagues, setLeagues] = useState<LeagueOption[]>([]);
  const [league, setLeague] = useState<string | null>(null);
  const [teams, setTeams] = useState<TeamOption[]>([]);
  const [homeTeam, setHomeTeam] = useState<string | null>(null);
  const [awayTeam, setAwayTeam] = useState<string | null>(null);
  const [count, setCount] = useState(10);
  const [running, setRunning] = useState(false);
  const [results, setResults] = useState<BatchResult[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchSports().then(setSports).catch(() => {});
  }, []);

  useEffect(() => {
    setLeague(null);
    setTeams([]);
    setHomeTeam(null);
    setAwayTeam(null);
    fetchLeagues(sport).then(setLeagues).catch(() => setLeagues([]));
    fetchTeams(sport).then(setTeams).catch(() => setTeams([]));
  }, [sport]);

  useEffect(() => {
    if (league) {
      fetchTeams(sport, league).then(setTeams).catch(() => setTeams([]));
    }
  }, [league, sport]);

  const handleRun = async () => {
    setRunning(true);
    setError(null);
    setResults([]);
    try {
      const data = await batchSimulate({
        sport,
        n: count,
        league,
        home_team: homeTeam,
        away_team: awayTeam,
      });
      setResults(data.results ?? []);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Batch failed');
    } finally {
      setRunning(false);
    }
  };

  const homeWins = results.filter((r) => r.winner === 'home').length;
  const awayWins = results.filter((r) => r.winner === 'away').length;
  const draws = results.length - homeWins - awayWins;

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <h2 className="text-2xl font-bold">Batch Simulation</h2>
      <p className="text-slate-400 text-sm">Run multiple simulations at once and compare aggregate results.</p>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {/* Sport */}
        <label className="space-y-1">
          <span className="text-xs text-slate-400">Sport</span>
          <select
            className="w-full rounded-lg bg-slate-800 border border-white/10 px-3 py-2 text-sm"
            value={sport}
            onChange={(e) => setSport(e.target.value)}
          >
            {sports.map((s) => (
              <option key={s} value={s}>{s}</option>
            ))}
          </select>
        </label>

        {/* League */}
        <label className="space-y-1">
          <span className="text-xs text-slate-400">League (optional)</span>
          <select
            className="w-full rounded-lg bg-slate-800 border border-white/10 px-3 py-2 text-sm"
            value={league ?? ''}
            onChange={(e) => setLeague(e.target.value || null)}
          >
            <option value="">Any</option>
            {leagues.map((l) => (
              <option key={l.id} value={l.id}>{l.name}</option>
            ))}
          </select>
        </label>

        {/* Count */}
        <label className="space-y-1">
          <span className="text-xs text-slate-400">Simulations</span>
          <input
            type="number"
            min={1}
            max={100}
            className="w-full rounded-lg bg-slate-800 border border-white/10 px-3 py-2 text-sm"
            value={count}
            onChange={(e) => setCount(Math.max(1, Math.min(100, Number(e.target.value))))}
          />
        </label>

        {/* Home team */}
        <label className="space-y-1">
          <span className="text-xs text-slate-400">Home Team (optional)</span>
          <select
            className="w-full rounded-lg bg-slate-800 border border-white/10 px-3 py-2 text-sm"
            value={homeTeam ?? ''}
            onChange={(e) => setHomeTeam(e.target.value || null)}
          >
            <option value="">Random</option>
            {teams.map((t) => (
              <option key={t.abbreviation} value={t.abbreviation}>{t.name}</option>
            ))}
          </select>
        </label>

        {/* Away team */}
        <label className="space-y-1">
          <span className="text-xs text-slate-400">Away Team (optional)</span>
          <select
            className="w-full rounded-lg bg-slate-800 border border-white/10 px-3 py-2 text-sm"
            value={awayTeam ?? ''}
            onChange={(e) => setAwayTeam(e.target.value || null)}
          >
            <option value="">Random</option>
            {teams.map((t) => (
              <option key={t.abbreviation} value={t.abbreviation}>{t.name}</option>
            ))}
          </select>
        </label>
      </div>

      <button
        onClick={handleRun}
        disabled={running}
        className="px-6 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-sm font-medium transition"
      >
        {running ? 'Running…' : `Run ${count} Simulations`}
      </button>

      {error && <p className="text-red-400 text-sm">{error}</p>}

      {results.length > 0 && (
        <div className="space-y-4">
          {/* Summary */}
          <div className="flex gap-4 text-sm">
            <span className="text-emerald-400">Home wins: {homeWins}</span>
            <span className="text-blue-400">Away wins: {awayWins}</span>
            <span className="text-slate-400">Draws: {draws}</span>
          </div>

          {/* Table */}
          <div className="overflow-x-auto rounded-xl border border-white/8">
            <table className="w-full text-sm">
              <thead className="bg-slate-800/60 text-slate-400">
                <tr>
                  <th className="px-4 py-2 text-left">#</th>
                  <th className="px-4 py-2 text-left">Game ID</th>
                  <th className="px-4 py-2 text-right">Home</th>
                  <th className="px-4 py-2 text-right">Away</th>
                  <th className="px-4 py-2 text-left">Winner</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/5">
                {results.map((r, i) => (
                  <tr key={r.game_id} className="hover:bg-white/5">
                    <td className="px-4 py-2 text-slate-500">{i + 1}</td>
                    <td className="px-4 py-2 font-mono text-xs">{r.game_id.slice(0, 8)}</td>
                    <td className="px-4 py-2 text-right">{r.home_score}</td>
                    <td className="px-4 py-2 text-right">{r.away_score}</td>
                    <td className="px-4 py-2 capitalize">{r.winner}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
