import { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { fetchTeams, fetchLeagues } from '../api';
import type { LeagueOption, SportType, TeamOption } from '../types';
import { getSportPresentation } from '../sportPresentation';
import { LEAGUE_SPORT } from '../sportUi';

export default function LeaguePage() {
  const { league } = useParams<{ league: string }>();
  const [teams, setTeams] = useState<TeamOption[]>([]);
  const [loading, setLoading] = useState(true);
  const [leagueName, setLeagueName] = useState<string>(league?.toUpperCase() ?? '');
  const sport = (league ? LEAGUE_SPORT[league.toLowerCase()] : 'soccer') as SportType;
  const presentation = getSportPresentation(sport);
  const primaryMoment = presentation.keyMoments[0] ?? presentation.label;

  useEffect(() => {
    if (!league) return;
    setLoading(true);

    // Fetch teams for this league
    fetchTeams(sport, league)
      .then((t) => setTeams(t))
      .catch(() => setTeams([]))
      .finally(() => setLoading(false));

    // Fetch league metadata for display name
    fetchLeagues(sport)
      .then((leagues) => {
        const match = leagues.find((l: LeagueOption) => l.id === league);
        if (match) setLeagueName(match.name);
      })
      .catch(() => {});
  }, [league]);

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      <section className={`rounded-[28px] border border-white/8 bg-gradient-to-br ${presentation.heroGradient} p-6 sm:p-8`}>
        <div className="space-y-3">
          <div className={`inline-flex rounded-full border px-3 py-1 text-[11px] uppercase tracking-[0.2em] ${presentation.accentBadge}`}>
            {presentation.label} League
          </div>
          <div>
            <h2 className="text-2xl sm:text-3xl font-bold">{leagueName || league?.toUpperCase()}</h2>
            <p className="mt-2 max-w-2xl text-sm text-slate-300">{presentation.headline}</p>
          </div>
          <div className="flex flex-wrap gap-2 text-xs text-slate-200">
            <span className="rounded-full border border-white/10 bg-white/5 px-3 py-1">{presentation.format}</span>
            <span className="rounded-full border border-white/10 bg-white/5 px-3 py-1">{presentation.keyMoments.join(' · ')}</span>
          </div>
        </div>
      </section>

      {loading && <p className="text-gray-500">Loading teams…</p>}

      {!loading && teams.length === 0 && (
        <p className="text-gray-500">No teams found for this league.</p>
      )}

      {!loading && teams.length > 0 && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
          {teams.map((t) => (
            <Link
              key={t.abbreviation}
              to={`/team/${t.abbreviation}?sport=${sport}&league=${league}`}
              className="block rounded-2xl border border-white/8 bg-slate-900/85 p-4 hover:border-blue-500/40 hover:-translate-y-0.5 transition"
            >
              <div className={`inline-flex rounded-full border px-2.5 py-1 text-[11px] ${presentation.accentBadge}`}>{t.abbreviation}</div>
              <div className="mt-3 font-semibold text-slate-100">{t.city} {t.name}</div>
              <div className="text-xs text-slate-400 mt-1">Built for {primaryMoment.toLowerCase()}</div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
