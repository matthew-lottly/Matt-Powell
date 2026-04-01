import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { listSimulations } from '../api';
import type { SimSummary } from '../types';
import { SPORT_LABELS, type SportType } from '../types';

export default function HistoryPage() {
  const [sims, setSims] = useState<SimSummary[]>([]);
  const [loading, setLoading] = useState(true);

  const refresh = () => {
    setLoading(true);
    listSimulations()
      .then(setSims)
      .catch(() => setSims([]))
      .finally(() => setLoading(false));
  };

  useEffect(() => { refresh(); }, []);

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold">Simulation History</h2>
        <div className="flex gap-2">
          <button
            onClick={refresh}
            disabled={loading}
            className="bg-gray-800 hover:bg-gray-700 text-gray-300 px-3 py-1.5 rounded-lg text-sm transition disabled:opacity-50"
          >
            {loading ? 'Loading…' : 'Refresh'}
          </button>
          <Link
            to="/simulate"
            className="bg-blue-600 hover:bg-blue-500 text-white px-3 py-1.5 rounded-lg text-sm transition"
          >
            New Sim
          </Link>
        </div>
      </div>

      {!loading && sims.length === 0 && (
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-6 text-center">
          <p className="text-gray-500">No simulations yet.</p>
          <Link to="/simulate" className="text-blue-400 text-sm hover:text-blue-300 mt-2 inline-block">
            Run your first simulation
          </Link>
        </div>
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
                  <td className="py-2 pr-4">
                    {SPORT_LABELS[s.sport as SportType] ?? s.sport}
                  </td>
                  <td className="py-2 pr-4">{s.home_team}</td>
                  <td className="py-2 pr-4">{s.away_team}</td>
                  <td className="py-2 pr-4 font-mono">
                    <span className={s.home_score > s.away_score ? 'text-blue-400 font-semibold' : ''}>{s.home_score}</span>
                    {' – '}
                    <span className={s.away_score > s.home_score ? 'text-red-400 font-semibold' : ''}>{s.away_score}</span>
                  </td>
                  <td className="py-2">
                    {s.is_finished ? (
                      <span className="text-green-400 text-xs font-medium bg-green-900/30 px-2 py-0.5 rounded-full">Finished</span>
                    ) : (
                      <span className="text-yellow-400 text-xs font-medium bg-yellow-900/30 px-2 py-0.5 rounded-full">In Progress</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {sims.length > 0 && (
        <div className="text-xs text-gray-600 text-center">
          {sims.length} simulation{sims.length !== 1 ? 's' : ''} · {sims.filter((s) => s.is_finished).length} finished
        </div>
      )}
    </div>
  );
}
