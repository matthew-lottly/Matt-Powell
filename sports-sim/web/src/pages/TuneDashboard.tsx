import './tune-dashboard.css';

export default function TuneDashboard() {
  const streamlitUrl = import.meta.env.VITE_TUNE_DASHBOARD_URL || 'http://localhost:8501';

  return (
    <div>
      <h2 className="text-xl font-semibold mb-2">Tuning Dashboard</h2>
      <p className="text-sm mb-3">Embedded dashboard (Streamlit). If not available, open in a new tab.</p>
      <div className="tune-dashboard-frame border rounded overflow-hidden">
        <iframe src={streamlitUrl} title="Tuning Dashboard" className="tune-dashboard-iframe" />
      </div>
      <p className="mt-2 text-xs text-gray-400">If the dashboard does not load, start the Streamlit service or set VITE_TUNE_DASHBOARD_URL.</p>
    </div>
  );
}
