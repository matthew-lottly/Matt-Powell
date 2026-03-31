import { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';

export default function PlayerPage() {
  const { id } = useParams();
  const [player, setPlayer] = useState<any | null>(null);

  useEffect(() => {
    // For now, this is a placeholder: player endpoint not implemented
    setPlayer({ id, name: 'Unknown', position: 'N/A' });
  }, [id]);

  if (!player) return <div>Loading player...</div>;
  return (
    <div>
      <h2 className="text-xl font-semibold mb-2">{player.name}</h2>
      <div>Position: {player.position}</div>
      <div>ID: {player.id}</div>
    </div>
  );
}
