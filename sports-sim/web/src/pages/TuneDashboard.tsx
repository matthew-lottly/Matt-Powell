import React from 'react';

export default function TuneDashboard() {
  const streamlitUrl = process.env.REACT_APP_TUNE_DASHBOARD_URL || 'http://localhost:8501';

  return (
    <div>
      <h2 className="text-xl font-semibold mb-2">Tuning Dashboard</h2>
      <p className="text-sm mb-3">Embedded dashboard (Streamlit). If not available, open in a new tab.</p>
      <div className="border rounded overflow-hidden" style={{height: '70vh'}}>
        <iframe src={streamlitUrl} title="Tuning Dashboard" style={{width: '100%', height: '100%', border: '0'}} />
      </div>
      <p className="mt-2 text-xs text-gray-400">If the dashboard does not load, start the Streamlit service or set REACT_APP_TUNE_DASHBOARD_URL.</p>
    </div>
  );
}
