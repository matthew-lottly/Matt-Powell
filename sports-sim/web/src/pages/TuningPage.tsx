import { useEffect, useState } from 'react';

type BestResult = {
  params?: Record<string, any>;
  score?: number;
};

export default function TuningPage() {
  const [best, setBest] = useState<BestResult | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    setLoading(true);
    fetch('/api/tuning/best')
      .then((r) => r.json())
      .then((j) => setBest(j))
      .catch(() => setBest(null))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div>
      <h2 className="text-xl font-semibold mb-2">Tuning — Best Candidate</h2>
      {loading && <div>Loading...</div>}
      {!loading && !best && <div>No data found.</div>}
      {!loading && best && (
        <div className="bg-gray-800 p-4 rounded-md text-sm">
          <div><strong>Score:</strong> {best.score}</div>
          <div className="mt-2"><strong>Params:</strong></div>
          <pre className="mt-1 text-xs">{JSON.stringify(best.params, null, 2)}</pre>
        </div>
      )}
    </div>
  );
}
