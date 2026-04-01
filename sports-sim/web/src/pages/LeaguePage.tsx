import { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { fetchTeams, fetchLeagues } from '../api';
import type { TeamOption } from '../types';

/** Map league id → sport so the teams endpoint knows what sport to query. */
const LEAGUE_SPORT: Record<string, string> = {
  nfl: 'football',
  nba: 'basketball',
  mlb: 'baseball',
  nhl: 'hockey',
  mls: 'soccer',
  epl: 'soccer',
  ncaasoc: 'soccer',
  npb: 'baseball',
  khl: 'hockey',
  euro: 'basketball',
  ipl: 'cricket',
};

export default function LeaguePage() {
  const { league } = useParams<{ league: string }>();
  const [teams, setTeams] = useState<TeamOption[]>([]);
  const [loading, setLoading] = useState(true);
  const [leagueName, setLeagueName] = useState<string>(league?.toUpperCase() ?? '');

  useEffect(() => {
    if (!league) return;
    setLoading(true);

    const sport = LEAGUE_SPORT[league.toLowerCase()] ?? 'soccer';

    // Fetch teams for this league
    fetchTeams(sport, league)
      .then((t) => setTeams(t))
      .catch(() => setTeams([]))
      .finally(() => setLoading(false));

    // Fetch league metadata for display name
    fetchLeagues(sport)
      .then((leagues) => {
        const match = leagues.find((l: any) => l.id === league);
        if (match) setLeagueName(match.name);
      })
      .catch(() => {});
  }, [league]);

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <h2 className="text-2xl font-bold">{leagueName || league?.toUpperCase()}</h2>

      {loading && <p className="text-gray-500">Loading teams…</p>}

      {!loading && teams.length === 0 && (
        <p className="text-gray-500">No teams found for this league.</p>
      )}

      {!loading && teams.length > 0 && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
          {teams.map((t) => (
            <Link
              key={t.abbreviation}
              to={`/team/${t.abbreviation}?sport=${LEAGUE_SPORT[league?.toLowerCase() ?? ''] ?? 'soccer'}&league=${league}`}
              className="block bg-gray-900 border border-gray-800 rounded-lg p-4 hover:border-blue-500 transition"
            >
              <div className="font-semibold text-gray-200">{t.name}</div>
              <div className="text-xs text-gray-500 mt-1">{t.city} · {t.abbreviation}</div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
