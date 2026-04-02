import { useEffect, useState } from 'react';
import { getSportPresentation } from '../sportPresentation';
import { getAccentFillColor, getTuningLensCopy, getTuningParamLabel } from '../sportUi';
import { SPORT_LABELS, type SportType } from '../types';

type TuningResult = {
  params?: Record<string, unknown>;
  score?: number;
  iteration?: number;
  timestamp?: string;
};

export default function TuningPage() {
  const [best, setBest] = useState<TuningResult | null>(null);
  const [results, setResults] = useState<TuningResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [showAll, setShowAll] = useState(false);
  const [lensSport, setLensSport] = useState<SportType>('soccer');

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
  const presentation = getSportPresentation(lensSport);
  const accentFill = getAccentFillColor(lensSport);
  const topParams = best?.params
    ? Object.entries(best.params)
        .filter(([, value]) => typeof value === 'number')
        .sort((left, right) => Number(right[1]) - Number(left[1]))
        .slice(0, 2)
    : [];

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold">Tuning Results</h2>
        <div className="flex items-center gap-2">
          <select
            value={lensSport}
            onChange={(event) => setLensSport(event.target.value as SportType)}
            aria-label="Select sport tuning lens"
            className="rounded-lg border border-white/10 bg-slate-900 px-3 py-1.5 text-sm text-slate-200"
          >
            {Object.entries(SPORT_LABELS).map(([value, label]) => (
              <option key={value} value={value}>{label} Lens</option>
            ))}
          </select>
          <button
            onClick={fetchData}
            disabled={loading}
            className="bg-gray-800 hover:bg-gray-700 text-gray-300 px-3 py-1.5 rounded-lg text-sm transition disabled:opacity-50"
          >
            {loading ? 'Loading…' : 'Refresh'}
          </button>
        </div>
      </div>

      <section className={`rounded-[28px] border border-white/8 bg-gradient-to-br ${presentation.heroGradient} p-6 sm:p-8`}>
        <div className={`inline-flex rounded-full border px-3 py-1 text-[11px] uppercase tracking-[0.2em] ${presentation.accentBadge}`}>
          {presentation.label} Tuning Lens
        </div>
        <h3 className="mt-3 text-xl font-semibold">Read the search space like a {presentation.label.toLowerCase()} system.</h3>
        <p className="mt-2 max-w-3xl text-sm text-slate-300">{getTuningLensCopy(lensSport)}</p>
        <div className="mt-4 flex flex-wrap gap-2">
          {presentation.keyMoments.map((moment) => (
            <span key={moment} className="rounded-full border border-white/10 bg-white/5 px-3 py-1 text-xs text-slate-200">{moment}</span>
          ))}
        </div>
      </section>

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
        <div className="bg-slate-900/85 border border-white/8 rounded-2xl p-5 space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-semibold text-slate-300">Best Candidate</h3>
            <div className="bg-green-900/40 text-green-400 px-3 py-1 rounded-full text-xs font-medium">
              Score: {typeof best!.score === 'number' ? best!.score.toFixed(4) : best!.score}
            </div>
          </div>

          {topParams.length > 0 && (
            <div className="grid gap-3 sm:grid-cols-2">
              {topParams.map(([key, value]) => (
                <div key={key} className="rounded-2xl border border-white/8 bg-black/10 p-4">
                  <div className="text-xs uppercase tracking-[0.16em] text-slate-500">Top influence</div>
                  <div className="mt-1 text-sm font-semibold text-slate-100">{getTuningParamLabel(lensSport, key)}</div>
                  <div className={`mt-2 text-2xl font-bold ${presentation.accentText}`}>{Number(value).toFixed(3)}</div>
                </div>
              ))}
            </div>
          )}

          {/* Params as visual bars */}
          {best!.params && (
            <div className="space-y-2">
              {Object.entries(best!.params).map(([key, val]) => {
                const numVal = typeof val === 'number' ? val : parseFloat(String(val));
                const isNumeric = !isNaN(numVal) && numVal >= 0 && numVal <= 2;
                return (
                  <div key={key} className="flex items-center gap-2 text-xs">
                    <span className="text-slate-400 w-40 shrink-0 font-mono">{getTuningParamLabel(lensSport, key)}</span>
                    {isNumeric ? (
                      <>
                        <svg viewBox="0 0 100 8" preserveAspectRatio="none" className="flex-1 h-2 overflow-hidden rounded-full bg-gray-800">
                          <rect x="0" y="0" width="100" height="8" rx="4" fill="#1f2937" />
                          <rect x="0" y="0" width={Math.min(100, numVal * 50)} height="8" rx="4" fill={accentFill} />
                        </svg>
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
            <div className="overflow-x-auto rounded-2xl border border-white/8 bg-slate-900/85 p-2">
              <table className="w-full text-sm text-left">
                <thead className="text-slate-400 border-b border-white/8 text-xs">
                  <tr>
                    <th className="py-2 pr-3">#</th>
                    <th className="py-2 pr-3">Score</th>
                    <th className="py-2">Params</th>
                  </tr>
                </thead>
                <tbody>
                  {results.map((r, i) => (
                    <tr key={i} className="border-b border-white/6 hover:bg-white/5">
                      <td className="py-2 pr-3 text-slate-500">{r.iteration ?? i + 1}</td>
                      <td className="py-2 pr-3 font-mono text-xs">
                        {typeof r.score === 'number' ? r.score.toFixed(4) : r.score ?? '—'}
                      </td>
                      <td className="py-2 text-xs text-slate-400 font-mono max-w-md truncate">
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
