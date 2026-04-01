import { useEffect, useState } from 'react';
import { useParams, useSearchParams, Link } from 'react-router-dom';

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
  const sport = searchParams.get('sport') ?? 'soccer';
  const league = searchParams.get('league');
  const [team, setTeam] = useState<TeamDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

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

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center gap-4">
        <div>
          <h2 className="text-2xl font-bold">{team.city} {team.name}</h2>
          <div className="text-sm text-gray-400">{team.abbreviation} · {sport.charAt(0).toUpperCase() + sport.slice(1)}{league ? ` · ${league.toUpperCase()}` : ''}</div>
        </div>
      </div>

      {/* Coach & Venue */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        {team.coach && (
          <div className="bg-gray-900 border border-gray-800 rounded-lg p-4">
            <h3 className="text-sm font-semibold text-gray-300 mb-2">Coach</h3>
            <div className="text-gray-200">{team.coach.name}</div>
            <div className="text-xs text-gray-500 capitalize">Style: {team.coach.style.replace(/_/g, ' ')}</div>
          </div>
        )}
        {team.venue && (
          <div className="bg-gray-900 border border-gray-800 rounded-lg p-4">
            <h3 className="text-sm font-semibold text-gray-300 mb-2">Venue</h3>
            <div className="text-gray-200">{team.venue.name}</div>
            <div className="text-xs text-gray-500">
              {team.venue.city} · {team.venue.surface} · Cap: {team.venue.capacity?.toLocaleString()}
            </div>
          </div>
        )}
      </div>

      {/* Active Roster */}
      <div>
        <h3 className="text-lg font-semibold mb-3">Active Roster ({team.players.length})</h3>
        <div className="overflow-x-auto">
          <table className="w-full text-sm text-left">
            <thead className="text-gray-400 border-b border-gray-800 text-xs">
              <tr>
                <th className="py-2 pr-3">#</th>
                <th className="py-2 pr-3">Name</th>
                <th className="py-2 pr-3">Pos</th>
                <th className="py-2 pr-3">Age</th>
                <th className="py-2 pr-3">SPD</th>
                <th className="py-2 pr-3">STR</th>
                <th className="py-2 pr-3">ACC</th>
                <th className="py-2 pr-3">END</th>
                <th className="py-2">SKL</th>
              </tr>
            </thead>
            <tbody>
              {team.players.map((p) => (
                <tr key={p.id} className="border-b border-gray-800/50 hover:bg-gray-900/50">
                  <td className="py-2 pr-3 text-gray-400">{p.number}</td>
                  <td className="py-2 pr-3">
                    <Link to={`/player/${p.id}?sport=${sport}&team=${abbr}&league=${league ?? ''}`} className="text-blue-400 hover:text-blue-300">
                      {p.name}
                    </Link>
                  </td>
                  <td className="py-2 pr-3 text-gray-400">{p.position}</td>
                  <td className="py-2 pr-3 text-gray-400">{p.age ?? '—'}</td>
                  <td className="py-2 pr-3">{p.attributes?.speed != null ? (p.attributes.speed * 100).toFixed(0) : '—'}</td>
                  <td className="py-2 pr-3">{p.attributes?.strength != null ? (p.attributes.strength * 100).toFixed(0) : '—'}</td>
                  <td className="py-2 pr-3">{p.attributes?.accuracy != null ? (p.attributes.accuracy * 100).toFixed(0) : '—'}</td>
                  <td className="py-2 pr-3">{p.attributes?.endurance != null ? (p.attributes.endurance * 100).toFixed(0) : '—'}</td>
                  <td className="py-2">{p.attributes?.skill != null ? (p.attributes.skill * 100).toFixed(0) : '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Bench */}
      {team.bench && team.bench.length > 0 && (
        <div>
          <h3 className="text-lg font-semibold mb-3">Bench ({team.bench.length})</h3>
          <div className="overflow-x-auto">
            <table className="w-full text-sm text-left">
              <thead className="text-gray-400 border-b border-gray-800 text-xs">
                <tr>
                  <th className="py-2 pr-3">#</th>
                  <th className="py-2 pr-3">Name</th>
                  <th className="py-2 pr-3">Pos</th>
                  <th className="py-2 pr-3">SPD</th>
                  <th className="py-2 pr-3">STR</th>
                  <th className="py-2 pr-3">ACC</th>
                  <th className="py-2 pr-3">END</th>
                  <th className="py-2">SKL</th>
                </tr>
              </thead>
              <tbody>
                {team.bench.map((p) => (
                  <tr key={p.id} className="border-b border-gray-800/50 hover:bg-gray-900/50">
                    <td className="py-2 pr-3 text-gray-400">{p.number}</td>
                    <td className="py-2 pr-3 text-gray-400">{p.name}</td>
                    <td className="py-2 pr-3 text-gray-400">{p.position}</td>
                    <td className="py-2 pr-3">{p.attributes?.speed != null ? (p.attributes.speed * 100).toFixed(0) : '—'}</td>
                    <td className="py-2 pr-3">{p.attributes?.strength != null ? (p.attributes.strength * 100).toFixed(0) : '—'}</td>
                    <td className="py-2 pr-3">{p.attributes?.accuracy != null ? (p.attributes.accuracy * 100).toFixed(0) : '—'}</td>
                    <td className="py-2 pr-3">{p.attributes?.endurance != null ? (p.attributes.endurance * 100).toFixed(0) : '—'}</td>
                    <td className="py-2">{p.attributes?.skill != null ? (p.attributes.skill * 100).toFixed(0) : '—'}</td>
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
