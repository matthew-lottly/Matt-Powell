import { useEffect, useState } from 'react';

type TuningResult = {
  params?: Record<string, any>;
  score?: number;
  iteration?: number;
  timestamp?: string;
};

export default function TuningPage() {
  const [best, setBest] = useState<TuningResult | null>(null);
  const [results, setResults] = useState<TuningResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [showAll, setShowAll] = useState(false);

  const fetchData = () => {
    setLoading(true);
    Promise.all([
      fetch('/api/tuning/best').then((r) => r.ok ? r.json() : null).catch(() => null),
      fetch('/api/tuning/results').then((r) => r.ok ? r.json() : []).catch(() => []),
    ])
      .then(([b, r]) => {
        setBest(b);
        setResults(Array.isArray(r) ? r : []);
      })
      .finally(() => setLoading(false));
  };

  useEffect(() => { fetchData(); }, []);

  const hasData = best && best.score != null;

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold">Tuning Results</h2>
        <button
          onClick={fetchData}
          disabled={loading}
          className="bg-gray-800 hover:bg-gray-700 text-gray-300 px-3 py-1.5 rounded-lg text-sm transition disabled:opacity-50"
        >
          {loading ? 'Loading…' : 'Refresh'}
        </button>
      </div>

      {/* Best Result Card */}
      {!loading && !hasData && (
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-6 text-center">
          <div className="text-gray-500">No tuning data yet.</div>
          <p className="text-xs text-gray-600 mt-2">
            Run the tuning API endpoint (<code className="text-gray-400">POST /api/tuning/tune</code>) to generate results,
            or the scheduler will run automatically if APScheduler is configured.
          </p>
        </div>
      )}

      {hasData && (
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-5 space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-semibold text-gray-300">Best Candidate</h3>
            <div className="bg-green-900/40 text-green-400 px-3 py-1 rounded-full text-xs font-medium">
              Score: {typeof best!.score === 'number' ? best!.score.toFixed(4) : best!.score}
            </div>
          </div>

          {/* Params as visual bars */}
          {best!.params && (
            <div className="space-y-2">
              {Object.entries(best!.params).map(([key, val]) => {
                const numVal = typeof val === 'number' ? val : parseFloat(val);
                const isNumeric = !isNaN(numVal) && numVal >= 0 && numVal <= 2;
                return (
                  <div key={key} className="flex items-center gap-2 text-xs">
                    <span className="text-gray-400 w-40 shrink-0 font-mono">{key}</span>
                    {isNumeric ? (
                      <>
                        <div className="flex-1 h-2 bg-gray-800 rounded-full overflow-hidden">
                          <div
                            className="h-full bg-blue-500 rounded-full"
                            style={{ width: `${Math.min(100, numVal * 50)}%` }}
                          />
                        </div>
                        <span className="text-gray-500 w-12 text-right">{numVal.toFixed(3)}</span>
                      </>
                    ) : (
                      <span className="text-gray-300">{String(val)}</span>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}

      {/* All Results Table */}
      {results.length > 0 && (
        <div>
          <button
            onClick={() => setShowAll(!showAll)}
            className="text-xs text-blue-400 hover:text-blue-300 mb-3"
          >
            {showAll ? '▾ Hide All Results' : `▸ Show All Results (${results.length})`}
          </button>

          {showAll && (
            <div className="overflow-x-auto">
              <table className="w-full text-sm text-left">
                <thead className="text-gray-400 border-b border-gray-800 text-xs">
                  <tr>
                    <th className="py-2 pr-3">#</th>
                    <th className="py-2 pr-3">Score</th>
                    <th className="py-2">Params</th>
                  </tr>
                </thead>
                <tbody>
                  {results.map((r, i) => (
                    <tr key={i} className="border-b border-gray-800/50 hover:bg-gray-900/50">
                      <td className="py-2 pr-3 text-gray-500">{r.iteration ?? i + 1}</td>
                      <td className="py-2 pr-3 font-mono text-xs">
                        {typeof r.score === 'number' ? r.score.toFixed(4) : r.score ?? '—'}
                      </td>
                      <td className="py-2 text-xs text-gray-400 font-mono max-w-md truncate">
                        {r.params ? JSON.stringify(r.params) : '—'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
