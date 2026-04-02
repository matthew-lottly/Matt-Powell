import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { fetchLeagues } from '../api';
import { SPORT_LABELS, type LeagueOption, type SportType } from '../types';
import { getSportPresentation } from '../sportPresentation';

interface LeagueInfo extends LeagueOption {
  sport: string;
}

const SPORTS: SportType[] = ['soccer', 'basketball', 'baseball', 'football', 'hockey', 'cricket'];

export default function LeaguesPage() {
  const [leagues, setLeagues] = useState<LeagueInfo[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    // Fetch leagues for all sports in parallel
    Promise.all(
      SPORTS.map((sport) =>
        fetchLeagues(sport).then((leagues) => leagues.map((league) => ({ ...league, sport })))
          .catch(() => [])
      )
    )
      .then((results) => setLeagues(results.flat()))
      .finally(() => setLoading(false));
  }, []);

  // Group by sport
  const grouped = leagues.reduce<Record<string, LeagueInfo[]>>((acc, l) => {
    (acc[l.sport] ??= []).push(l);
    return acc;
  }, {});

  return (
    <div className="max-w-5xl mx-auto space-y-8">
      <section className="rounded-[28px] border border-white/8 bg-gradient-to-br from-slate-900 via-slate-950 to-slate-900 p-6 sm:p-8">
        <div className="inline-flex rounded-full border border-blue-400/20 bg-blue-500/10 px-3 py-1 text-[11px] uppercase tracking-[0.2em] text-blue-200">
          Competition Browser
        </div>
        <h2 className="mt-3 text-2xl sm:text-3xl font-bold">Leagues by Sport</h2>
        <p className="mt-2 max-w-2xl text-sm text-slate-300">
          Browse roster-backed competitions, then jump directly into a league-specific matchup flow.
        </p>
      </section>

      {loading && <p className="text-gray-500">Loading leagues…</p>}

      {!loading && leagues.length === 0 && (
        <p className="text-gray-500">No leagues found.</p>
      )}

      {!loading && Object.entries(grouped).map(([sport, sportLeagues]) => (
        <div key={sport}>
          <div className="mb-4 rounded-2xl border border-white/8 bg-slate-900/70 p-4">
            <div className={`inline-flex rounded-full border px-2.5 py-1 text-[11px] ${getSportPresentation(sport as SportType).accentBadge}`}>
              {SPORT_LABELS[sport as SportType] ?? sport}
            </div>
            <p className="mt-2 text-sm text-slate-300">{getSportPresentation(sport as SportType).headline}</p>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
            {sportLeagues.map((l) => (
              <Link
                key={l.id}
                to={`/league/${l.id}`}
                className="block bg-slate-900/85 border border-white/8 rounded-2xl p-4 hover:border-blue-500/40 hover:-translate-y-0.5 transition"
              >
                <div className="font-semibold text-slate-100">{l.name}</div>
                <div className="flex gap-2 mt-2 text-xs">
                  {l.roster_available && (
                    <span className="bg-green-900/40 text-green-400 px-2 py-0.5 rounded-full">Rosters</span>
                  )}
                  {l.venues && (
                    <span className="bg-blue-900/40 text-blue-400 px-2 py-0.5 rounded-full">Venues</span>
                  )}
                  {l.country && (
                    <span className="text-slate-500">{l.country}</span>
                  )}
                </div>
                <div className="mt-3 text-xs text-slate-400">{getSportPresentation(sport as SportType).keyMoments[0]}</div>
              </Link>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}
