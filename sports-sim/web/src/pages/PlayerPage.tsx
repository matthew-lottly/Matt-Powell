import { useEffect, useState } from 'react';
import { useParams, useSearchParams, Link } from 'react-router-dom';

interface PlayerDetail {
  id: string;
  name: string;
  number: number;
  position: string;
  age?: number;
  height_cm?: number;
  weight_kg?: number;
  is_bench: boolean;
  attributes: Record<string, number>;
  team: { abbreviation: string; name: string; city: string };
}

/** Friendly labels for attribute keys */
const ATTR_LABELS: Record<string, string> = {
  speed: 'Speed',
  strength: 'Strength',
  accuracy: 'Accuracy',
  endurance: 'Endurance',
  skill: 'Skill',
  decision_making: 'Decision Making',
  aggression: 'Aggression',
  composure: 'Composure',
};

function AttrBar({ label, value }: { label: string; value: number }) {
  const pct = Math.round(value * 100);
  const color =
    pct >= 80 ? 'bg-green-500' : pct >= 60 ? 'bg-blue-500' : pct >= 40 ? 'bg-yellow-500' : 'bg-red-500';
  return (
    <div className="flex items-center gap-2 text-xs">
      <span className="text-gray-400 w-28 shrink-0">{label}</span>
      <div className="flex-1 h-2 bg-gray-800 rounded-full overflow-hidden">
        <div className={`h-full ${color} rounded-full transition-all`} style={{ width: `${pct}%` }} />
      </div>
      <span className="text-gray-500 w-8 text-right">{pct}</span>
    </div>
  );
}

export default function PlayerPage() {
  const { id } = useParams();
  const [searchParams] = useSearchParams();
  const sport = searchParams.get('sport') ?? 'soccer';
  const team = searchParams.get('team') ?? '';
  const league = searchParams.get('league');
  const [player, setPlayer] = useState<PlayerDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!id || !team) {
      setError('Missing team or player ID');
      setLoading(false);
      return;
    }
    setLoading(true);
    setError(null);
    const leagueQ = league ? `?league=${encodeURIComponent(league)}` : '';
    fetch(`/api/players/${encodeURIComponent(sport)}/${encodeURIComponent(team)}/${encodeURIComponent(id)}${leagueQ}`)
      .then((r) => {
        if (!r.ok) throw new Error(`Player not found (${r.status})`);
        return r.json();
      })
      .then((j) => setPlayer(j))
      .catch((e) => {
        setPlayer(null);
        setError(e.message);
      })
      .finally(() => setLoading(false));
  }, [id, sport, team, league]);

  if (loading) return <div className="text-gray-500 p-6">Loading player…</div>;
  if (error) return <div className="text-red-400 p-6">{error}</div>;
  if (!player) return <div className="text-gray-500 p-6">Player not found.</div>;

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      {/* Header */}
      <div>
        <div className="text-sm text-gray-500">
          <Link to={`/team/${player.team.abbreviation}?sport=${sport}&league=${league ?? ''}`} className="text-blue-400 hover:text-blue-300">
            {player.team.city} {player.team.name}
          </Link>
          {' · '}{sport.charAt(0).toUpperCase() + sport.slice(1)}
        </div>
        <h2 className="text-2xl font-bold mt-1">
          <span className="text-gray-500 mr-2">#{player.number}</span>
          {player.name}
        </h2>
        <div className="flex gap-3 mt-2 text-sm text-gray-400">
          <span>{player.position}</span>
          {player.age && <span>· Age {player.age}</span>}
          {player.height_cm && <span>· {player.height_cm} cm</span>}
          {player.weight_kg && <span>· {player.weight_kg} kg</span>}
          <span>· {player.is_bench ? 'Bench' : 'Starter'}</span>
        </div>
      </div>

      {/* Attributes */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-5 space-y-3">
        <h3 className="text-sm font-semibold text-gray-300 mb-3">Attributes</h3>
        {Object.entries(player.attributes).map(([key, val]) => (
          <AttrBar key={key} label={ATTR_LABELS[key] ?? key} value={val} />
        ))}
      </div>

      {/* Overall rating */}
      {Object.keys(player.attributes).length > 0 && (
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-5 text-center">
          <div className="text-xs text-gray-500 mb-1">Overall Rating</div>
          <div className="text-4xl font-extrabold text-blue-400">
            {Math.round((Object.values(player.attributes).reduce((a, b) => a + b, 0) / Object.values(player.attributes).length) * 100)}
          </div>
        </div>
      )}

      {/* Nav */}
      <div className="flex gap-3">
        <Link
          to={`/team/${player.team.abbreviation}?sport=${sport}&league=${league ?? ''}`}
          className="bg-gray-800 hover:bg-gray-700 text-gray-300 px-4 py-2 rounded-lg text-sm transition"
        >
          Back to {player.team.name}
        </Link>
      </div>
    </div>
  );
}
