import { useEffect, useState } from 'react';
import { useParams, useSearchParams, Link } from 'react-router-dom';
import { getSportPresentation } from '../sportPresentation';
import { attributeAverage, averagePlayerRating, getSportAttributeLabel, getSportRosterColumns, getSportRosterLabels, topAttribute } from '../sportUi';
import type { SportType } from '../types';

interface PlayerInfo {
  id: string;
  name: string;
  number: number;
  position: string;
  age?: number;
  height_cm?: number;
  weight_kg?: number;
  attributes?: Record<string, number>;
}

interface TeamDetail {
  abbreviation: string;
  name: string;
  city: string;
  coach?: { name: string; style: string };
  venue?: { name: string; city: string; venue_type: string; surface: string; capacity: number; altitude_m: number; weather_exposed: boolean };
  players: PlayerInfo[];
  bench: PlayerInfo[];
}

export default function TeamPage() {
  const { abbr } = useParams();
  const [searchParams] = useSearchParams();
  const sport = (searchParams.get('sport') ?? 'soccer') as SportType;
  const league = searchParams.get('league');
  const [team, setTeam] = useState<TeamDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const presentation = getSportPresentation(sport);
  const rosterLabels = getSportRosterLabels(sport);
  const statColumns = getSportRosterColumns(sport);

  useEffect(() => {
    if (!abbr) return;
    setLoading(true);
    setError(null);
    const leagueQ = league ? `?league=${encodeURIComponent(league)}` : '';
    fetch(`/api/teams/${encodeURIComponent(sport)}/${encodeURIComponent(abbr)}${leagueQ}`)
      .then((r) => {
        if (!r.ok) throw new Error(`Team not found (${r.status})`);
        return r.json();
      })
      .then((j) => setTeam(j))
      .catch((e) => {
        setTeam(null);
        setError(e.message);
      })
      .finally(() => setLoading(false));
  }, [abbr, sport, league]);

  if (loading) return <div className="text-gray-500 p-6">Loading team…</div>;
  if (error) return <div className="text-red-400 p-6">{error}</div>;
  if (!team) return <div className="text-gray-500 p-6">Team not found.</div>;

  const starterRating = averagePlayerRating(team.players);
  const benchRating = averagePlayerRating(team.bench);
  const topPlayers = [...team.players]
    .sort((left, right) => attributeAverage(right.attributes ?? {}) - attributeAverage(left.attributes ?? {}))
    .slice(0, 3);

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      <section className={`rounded-[28px] border border-white/8 bg-gradient-to-br ${presentation.heroGradient} p-6 sm:p-8`}>
        <div className="space-y-4">
          <div className={`inline-flex rounded-full border px-3 py-1 text-[11px] uppercase tracking-[0.2em] ${presentation.accentBadge}`}>
            {presentation.label} Team Profile
          </div>
          <div>
            <h2 className="text-2xl sm:text-3xl font-bold">{team.city} {team.name}</h2>
            <div className="mt-2 text-sm text-slate-300">{team.abbreviation} · {presentation.format}{league ? ` · ${league.toUpperCase()}` : ''}</div>
          </div>
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4 text-xs">
            <div className="rounded-2xl border border-white/10 bg-black/10 p-3">
              <div className="text-slate-500 uppercase tracking-[0.16em]">{rosterLabels.starterMetric}</div>
              <div className={`mt-1 text-2xl font-bold ${presentation.accentText}`}>{starterRating}</div>
            </div>
            <div className="rounded-2xl border border-white/10 bg-black/10 p-3">
              <div className="text-slate-500 uppercase tracking-[0.16em]">{rosterLabels.benchMetric}</div>
              <div className={`mt-1 text-2xl font-bold ${presentation.accentText}`}>{benchRating}</div>
            </div>
            <div className="rounded-2xl border border-white/10 bg-black/10 p-3">
              <div className="text-slate-500 uppercase tracking-[0.16em]">Active Squad</div>
              <div className="mt-1 text-2xl font-bold text-slate-100">{team.players.length}</div>
            </div>
            <div className="rounded-2xl border border-white/10 bg-black/10 p-3">
              <div className="text-slate-500 uppercase tracking-[0.16em]">Focus</div>
              <div className="mt-1 text-sm text-slate-100">{presentation.keyMoments[0]}</div>
            </div>
          </div>
        </div>
      </section>

      {/* Coach & Venue */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        {team.coach && (
          <div className="bg-slate-900/85 border border-white/8 rounded-2xl p-4">
            <h3 className="text-sm font-semibold text-slate-200 mb-2">Coach</h3>
            <div className="text-slate-100">{team.coach.name}</div>
            <div className="text-xs text-slate-400 capitalize">Style: {team.coach.style.replace(/_/g, ' ')}</div>
          </div>
        )}
        {team.venue && (
          <div className="bg-slate-900/85 border border-white/8 rounded-2xl p-4">
            <h3 className="text-sm font-semibold text-slate-200 mb-2">Venue</h3>
            <div className="text-slate-100">{team.venue.name}</div>
            <div className="text-xs text-slate-400">
              {team.venue.city} · {team.venue.surface} · Cap: {team.venue.capacity?.toLocaleString()}
            </div>
          </div>
        )}
      </div>

      {topPlayers.length > 0 && (
        <div className="rounded-2xl border border-white/8 bg-slate-900/85 p-4">
          <div className="text-sm font-semibold text-slate-200 mb-3">Impact Players</div>
          <div className="grid gap-3 sm:grid-cols-3">
            {topPlayers.map((player) => {
              const trait = topAttribute(player.attributes ?? {});
              return (
                <Link
                  key={player.id}
                  to={`/player/${player.id}?sport=${sport}&team=${abbr}&league=${league ?? ''}`}
                  className="rounded-2xl border border-white/8 bg-black/10 p-4 hover:bg-white/5 transition"
                >
                  <div className="text-sm font-semibold text-slate-100">#{player.number} {player.name}</div>
                  <div className="mt-1 text-xs text-slate-400">{player.position}</div>
                  {trait && <div className={`mt-3 inline-flex rounded-full border px-2.5 py-1 text-[11px] ${presentation.accentBadge}`}>{getSportAttributeLabel(sport, trait.key)} · {trait.value}</div>}
                </Link>
              );
            })}
          </div>
        </div>
      )}

      {/* Active Roster */}
      <div>
        <h3 className="text-lg font-semibold mb-3">{rosterLabels.starters} ({team.players.length})</h3>
        <div className="overflow-x-auto rounded-2xl border border-white/8 bg-slate-900/85 p-2">
          <table className="w-full text-sm text-left">
            <thead className="text-slate-400 border-b border-white/8 text-xs">
              <tr>
                <th className="py-2 pr-3">#</th>
                <th className="py-2 pr-3">Name</th>
                <th className="py-2 pr-3">Pos</th>
                <th className="py-2 pr-3">Age</th>
                {statColumns.map((column) => (
                  <th key={column.key} className="py-2 pr-3">{column.shortLabel}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {team.players.map((p) => (
                <tr key={p.id} className="border-b border-white/6 hover:bg-white/5">
                  <td className="py-2 pr-3 text-slate-400">{p.number}</td>
                  <td className="py-2 pr-3">
                    <Link to={`/player/${p.id}?sport=${sport}&team=${abbr}&league=${league ?? ''}`} className="text-blue-400 hover:text-blue-300">
                      {p.name}
                    </Link>
                  </td>
                  <td className="py-2 pr-3 text-slate-400">{p.position}</td>
                  <td className="py-2 pr-3 text-slate-400">{p.age ?? '—'}</td>
                  {statColumns.map((column) => (
                    <td key={column.key} className="py-2 pr-3">
                      {p.attributes?.[column.key] != null ? ((p.attributes?.[column.key] ?? 0) * 100).toFixed(0) : '—'}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Bench */}
      {team.bench && team.bench.length > 0 && (
        <div>
          <h3 className="text-lg font-semibold mb-3">{rosterLabels.bench} ({team.bench.length})</h3>
          <div className="overflow-x-auto rounded-2xl border border-white/8 bg-slate-900/85 p-2">
            <table className="w-full text-sm text-left">
              <thead className="text-slate-400 border-b border-white/8 text-xs">
                <tr>
                  <th className="py-2 pr-3">#</th>
                  <th className="py-2 pr-3">Name</th>
                  <th className="py-2 pr-3">Pos</th>
                  {statColumns.map((column) => (
                    <th key={column.key} className="py-2 pr-3">{column.shortLabel}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {team.bench.map((p) => (
                  <tr key={p.id} className="border-b border-white/6 hover:bg-white/5">
                    <td className="py-2 pr-3 text-slate-400">{p.number}</td>
                    <td className="py-2 pr-3 text-slate-200">{p.name}</td>
                    <td className="py-2 pr-3 text-slate-400">{p.position}</td>
                    {statColumns.map((column) => (
                      <td key={column.key} className="py-2 pr-3">
                        {p.attributes?.[column.key] != null ? ((p.attributes?.[column.key] ?? 0) * 100).toFixed(0) : '—'}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Quick action */}
      <div className="flex gap-3">
        <Link
          to={`/simulate?sport=${sport}&home=${abbr}`}
          className="bg-blue-600 hover:bg-blue-500 text-white px-4 py-2 rounded-lg text-sm transition"
        >
          Simulate with {team.name}
        </Link>
        {league && (
          <Link
            to={`/league/${league}`}
            className="bg-gray-800 hover:bg-gray-700 text-gray-300 px-4 py-2 rounded-lg text-sm transition"
          >
            Back to League
          </Link>
        )}
      </div>
    </div>
  );
}
