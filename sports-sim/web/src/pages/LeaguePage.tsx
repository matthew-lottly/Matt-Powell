import { useEffect, useState } from 'react';

export default function LeaguePage() {
  const [teams, setTeams] = useState<any[]>([]);

  useEffect(() => {
    fetch('/api/teams/soccer?league=mls')
      .then((r) => r.json())
      .then((j) => setTeams(j.teams || []))
      .catch(() => setTeams([]));
  }, []);

  return (
    <div>
      <h2 className="text-xl font-semibold mb-2">League Teams</h2>
      <ul>
        {teams.map((t) => (
          <li key={t.abbreviation} className="py-1">
            {t.abbreviation} — {t.name}
          </li>
        ))}
      </ul>
    </div>
  );
}
