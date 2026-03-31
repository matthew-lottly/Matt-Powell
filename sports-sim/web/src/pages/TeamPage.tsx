import { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';

export default function TeamPage() {
  const { abbr } = useParams();
  const [team, setTeam] = useState<any | null>(null);

  useEffect(() => {
    if (!abbr) return;
    fetch(`/api/teams/soccer/${abbr}`)
      .then((r) => r.json())
      .then((j) => setTeam(j))
      .catch(() => setTeam(null));
  }, [abbr]);

  if (!team) return <div>Loading team...</div>;
  return (
    <div>
      <h2 className="text-xl font-semibold mb-2">{team.name} ({team.abbreviation})</h2>
      <div>Coach: {team.coach?.name}</div>
      <h3 className="mt-3">Players</h3>
      <ul>
        {team.players.map((p: any) => (
          <li key={p.id}>{p.number} — {p.name} ({p.position})</li>
        ))}
      </ul>
    </div>
  );
}
