import { useEffect, useState } from 'react';
import { listSimulations } from '../api';
import type { SimSummary } from '../types';

export default function HistoryPage() {
  const [sims, setSims] = useState<SimSummary[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    listSimulations()
      .then(setSims)
      .catch(() => setSims([]))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <h2 className="text-2xl font-bold">Simulation History</h2>

      {loading && <p className="text-gray-500">Loading…</p>}

      {!loading && sims.length === 0 && (
        <p className="text-gray-500">No simulations yet. Go run one!</p>
      )}

      {sims.length > 0 && (
        <div className="overflow-x-auto">
          <table className="w-full text-sm text-left">
            <thead className="text-gray-400 border-b border-gray-800">
              <tr>
                <th className="py-2 pr-4">Sport</th>
                <th className="py-2 pr-4">Home</th>
                <th className="py-2 pr-4">Away</th>
                <th className="py-2 pr-4">Score</th>
                <th className="py-2">Status</th>
              </tr>
            </thead>
            <tbody>
              {sims.map((s) => (
                <tr key={s.game_id} className="border-b border-gray-800/50 hover:bg-gray-900">
                  <td className="py-2 pr-4 capitalize">{s.sport}</td>
                  <td className="py-2 pr-4">{s.home_team}</td>
                  <td className="py-2 pr-4">{s.away_team}</td>
                  <td className="py-2 pr-4 font-mono">
                    {s.home_score} – {s.away_score}
                  </td>
                  <td className="py-2">
                    {s.is_finished ? (
                      <span className="text-green-400">Finished</span>
                    ) : (
                      <span className="text-yellow-400">In Progress</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
