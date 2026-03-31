import { Routes, Route } from 'react-router-dom';
import Layout from './components/Layout';
import HomePage from './pages/HomePage';
import SimulationPage from './pages/SimulationPage';
import HistoryPage from './pages/HistoryPage';
import TuningPage from './pages/TuningPage';
import LeaguePage from './pages/LeaguePage';
import TeamPage from './pages/TeamPage';
import PlayerPage from './pages/PlayerPage';
import TuneDashboard from './pages/TuneDashboard';

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route path="/" element={<HomePage />} />
        <Route path="/simulate" element={<SimulationPage />} />
        <Route path="/history" element={<HistoryPage />} />
        <Route path="/tuning" element={<TuningPage />} />
        <Route path="/dashboard" element={<TuneDashboard />} />
        <Route path="/league/:league" element={<LeaguePage />} />
        <Route path="/team/:abbr" element={<TeamPage />} />
        <Route path="/player/:id" element={<PlayerPage />} />
      </Route>
    </Routes>
  );
}
