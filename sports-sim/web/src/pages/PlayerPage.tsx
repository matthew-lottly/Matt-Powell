import { useEffect, useState } from 'react';
import { useParams, useSearchParams, Link } from 'react-router-dom';
import { getSportPresentation } from '../sportPresentation';
import { attributeAverage, getSportAttributeLabel, topAttribute } from '../sportUi';
import type { SportType } from '../types';

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

function AttrBar({ label, value }: { label: string; value: number }) {
  const pct = Math.round(value * 100);
  const color =
    pct >= 80 ? '#22c55e' : pct >= 60 ? '#3b82f6' : pct >= 40 ? '#eab308' : '#ef4444';
  return (
    <div className="flex items-center gap-2 text-xs">
      <span className="text-gray-400 w-28 shrink-0">{label}</span>
      <svg viewBox="0 0 100 8" preserveAspectRatio="none" className="flex-1 h-2 overflow-hidden rounded-full bg-gray-800">
        <rect x="0" y="0" width="100" height="8" rx="4" fill="#1f2937" />
        <rect x="0" y="0" width={pct} height="8" rx="4" fill={color} />
      </svg>
      <span className="text-gray-500 w-8 text-right">{pct}</span>
    </div>
  );
}

export default function PlayerPage() {
  const { id } = useParams();
  const [searchParams] = useSearchParams();
  const sport = (searchParams.get('sport') ?? 'soccer') as SportType;
  const team = searchParams.get('team') ?? '';
  const league = searchParams.get('league');
  const [player, setPlayer] = useState<PlayerDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const presentation = getSportPresentation(sport);
  const primaryMoment = presentation.keyMoments[0] ?? presentation.label;
  const secondaryMoment = presentation.keyMoments[1] ?? presentation.rhythm;

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

  const overall = attributeAverage(player.attributes);
  const signature = topAttribute(player.attributes);

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      {/* Header */}
      <section className={`rounded-[28px] border border-white/8 bg-gradient-to-br ${presentation.heroGradient} p-6 sm:p-8`}>
        <div className="text-sm text-slate-400">
          <Link to={`/team/${player.team.abbreviation}?sport=${sport}&league=${league ?? ''}`} className="text-blue-400 hover:text-blue-300">
            {player.team.city} {player.team.name}
          </Link>
          {' · '}{sport.charAt(0).toUpperCase() + sport.slice(1)}
        </div>
        <h2 className="text-2xl sm:text-3xl font-bold mt-2">
          <span className="text-slate-500 mr-2">#{player.number}</span>
          {player.name}
        </h2>
        <div className="flex flex-wrap gap-3 mt-3 text-sm text-slate-300">
          <span>{player.position}</span>
          {player.age && <span>· Age {player.age}</span>}
          {player.height_cm && <span>· {player.height_cm} cm</span>}
          {player.weight_kg && <span>· {player.weight_kg} kg</span>}
          <span>· {player.is_bench ? 'Bench' : 'Starter'}</span>
        </div>
        <div className="mt-4 grid grid-cols-2 sm:grid-cols-3 gap-3 text-xs">
          <div className="rounded-2xl border border-white/10 bg-black/10 p-3">
            <div className="text-slate-500 uppercase tracking-[0.16em]">Overall</div>
            <div className={`mt-1 text-2xl font-bold ${presentation.accentText}`}>{overall}</div>
          </div>
          <div className="rounded-2xl border border-white/10 bg-black/10 p-3">
            <div className="text-slate-500 uppercase tracking-[0.16em]">Signature</div>
            <div className="mt-1 text-sm text-slate-100">
              {signature ? `${getSportAttributeLabel(sport, signature.key)} ${signature.value}` : 'Balanced'}
            </div>
          </div>
          <div className="rounded-2xl border border-white/10 bg-black/10 p-3 col-span-2 sm:col-span-1">
            <div className="text-slate-500 uppercase tracking-[0.16em]">Game Lens</div>
            <div className="mt-1 text-sm text-slate-100">{primaryMoment}</div>
          </div>
        </div>
      </section>

      {/* Attributes */}
      <div className="bg-slate-900/85 border border-white/8 rounded-2xl p-5 space-y-3">
        <h3 className="text-sm font-semibold text-slate-200 mb-3">Attributes</h3>
        {Object.entries(player.attributes).map(([key, val]) => (
          <AttrBar key={key} label={getSportAttributeLabel(sport, key)} value={val} />
        ))}
      </div>

      {/* Overall rating */}
      {Object.keys(player.attributes).length > 0 && (
        <div className="bg-slate-900/85 border border-white/8 rounded-2xl p-5 text-center">
          <div className="text-xs text-slate-500 mb-1">{presentation.label} Profile Read</div>
          <div className={`text-4xl font-extrabold ${presentation.accentText}`}>
            {overall}
          </div>
          <p className="mt-2 text-sm text-slate-400">Best used for {primaryMoment.toLowerCase()} and {secondaryMoment.toLowerCase()}.</p>
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
