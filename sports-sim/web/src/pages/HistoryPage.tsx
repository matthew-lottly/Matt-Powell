import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { listSimulations, deleteSimulation } from '../api';
import type { SimSummary } from '../types';
import { SPORT_LABELS, type SportType } from '../types';
import { getSportPresentation } from '../sportPresentation';
import { formatSimulationScore } from '../sportUi';

export default function HistoryPage() {
  const [sims, setSims] = useState<SimSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [deletingId, setDeletingId] = useState<string | null>(null);

  const refresh = () => {
    setLoading(true);
    listSimulations()
      .then(setSims)
      .catch(() => setSims([]))
      .finally(() => setLoading(false));
  };

  useEffect(() => { refresh(); }, []);

  const handleDelete = async (gameId: string, label: string) => {
    if (!window.confirm(`Delete simulation "${label}"? This cannot be undone.`)) return;
    setDeletingId(gameId);
    try {
      await deleteSimulation(gameId);
      setSims((prev) => prev.filter((s) => s.game_id !== gameId));
    } catch {
      // silently fail — sim may already be gone
    } finally {
      setDeletingId(null);
    }
  };

  return (
    <div className="max-w-5xl mx-auto space-y-6">
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
        <div className="grid gap-3">
          {sims.map((simulation) => {
            const sport = simulation.sport as SportType;
            const presentation = getSportPresentation(sport);
            return (
              <div key={simulation.game_id} className="rounded-2xl border border-white/8 bg-slate-900/85 p-4">
                <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                  <div>
                    <div className={`inline-flex rounded-full border px-2.5 py-1 text-[11px] ${presentation.accentBadge}`}>
                      {SPORT_LABELS[sport] ?? simulation.sport}
                    </div>
                    <div className="mt-3 text-lg font-semibold text-slate-100">{simulation.home_team} vs {simulation.away_team}</div>
                    <div className="mt-1 text-sm text-slate-400">{formatSimulationScore(sport, simulation.home_score, simulation.away_score)}</div>
                  </div>
                  <div className="text-right">
                    <div className={`text-2xl font-bold ${presentation.accentText}`}>
                      {simulation.home_score} - {simulation.away_score}
                    </div>
                    <div className="mt-2 text-xs text-slate-400">{presentation.rhythm}</div>
                    <div className="mt-2">
                      {simulation.is_finished ? (
                        <span className="text-green-400 text-xs font-medium bg-green-900/30 px-2 py-0.5 rounded-full">Finished</span>
                      ) : (
                        <span className="text-yellow-400 text-xs font-medium bg-yellow-900/30 px-2 py-0.5 rounded-full">In Progress</span>
                      )}
                    </div>
                    <button
                      onClick={() => handleDelete(simulation.game_id, `${simulation.home_team} vs ${simulation.away_team}`)}
                      disabled={deletingId === simulation.game_id}
                      className="mt-2 text-xs text-red-400 hover:text-red-300 disabled:opacity-50 transition"
                    >
                      {deletingId === simulation.game_id ? 'Deleting…' : 'Delete'}
                    </button>
                  </div>
                </div>
              </div>
            );
          })}
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
