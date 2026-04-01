import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { SPORT_LABELS, type SportType } from '../types';

interface LeagueInfo {
  id: string;
  name: string;
  sport: string;
  country?: string;
  roster_available?: boolean;
  venues?: boolean;
  source?: string;
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
        fetch(`/api/leagues?sport=${sport}`)
          .then((r) => r.ok ? r.json() : { leagues: [] })
          .then((data) =>
            (data.leagues ?? []).map((l: any) => ({ ...l, sport }))
          )
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
    <div className="max-w-4xl mx-auto space-y-8">
      <h2 className="text-2xl font-bold">Leagues</h2>

      {loading && <p className="text-gray-500">Loading leagues…</p>}

      {!loading && leagues.length === 0 && (
        <p className="text-gray-500">No leagues found.</p>
      )}

      {!loading && Object.entries(grouped).map(([sport, sportLeagues]) => (
        <div key={sport}>
          <h3 className="text-lg font-semibold text-gray-300 mb-3">
            {SPORT_LABELS[sport as SportType] ?? sport}
          </h3>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
            {sportLeagues.map((l) => (
              <Link
                key={l.id}
                to={`/league/${l.id}`}
                className="block bg-gray-900 border border-gray-800 rounded-lg p-4 hover:border-blue-500 transition"
              >
                <div className="font-semibold text-gray-200">{l.name}</div>
                <div className="flex gap-2 mt-2 text-xs">
                  {l.roster_available && (
                    <span className="bg-green-900/40 text-green-400 px-2 py-0.5 rounded-full">Rosters</span>
                  )}
                  {l.venues && (
                    <span className="bg-blue-900/40 text-blue-400 px-2 py-0.5 rounded-full">Venues</span>
                  )}
                  {l.country && (
                    <span className="text-gray-500">{l.country}</span>
                  )}
                </div>
              </Link>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}
