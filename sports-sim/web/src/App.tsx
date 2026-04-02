import { Routes, Route } from 'react-router-dom';
import Layout from './components/Layout';
import HomePage from './pages/HomePage';
import SimulationPage from './pages/SimulationPage';
import HistoryPage from './pages/HistoryPage';
import TuningPage from './pages/TuningPage';
import LeaguePage from './pages/LeaguePage';
import LeaguesPage from './pages/LeaguesPage';
import TeamPage from './pages/TeamPage';
import PlayerPage from './pages/PlayerPage';
import TuneDashboard from './pages/TuneDashboard';
import BatchPage from './pages/BatchPage';
import NotFound from './pages/NotFound';

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route path="/" element={<HomePage />} />
        <Route path="/simulate" element={<SimulationPage />} />
        <Route path="/history" element={<HistoryPage />} />
        <Route path="/batch" element={<BatchPage />} />
        <Route path="/leagues" element={<LeaguesPage />} />
        <Route path="/tuning" element={<TuningPage />} />
        <Route path="/dashboard" element={<TuneDashboard />} />
        <Route path="/league/:league" element={<LeaguePage />} />
        <Route path="/team/:abbr" element={<TeamPage />} />
        <Route path="/player/:id" element={<PlayerPage />} />
        <Route path="*" element={<NotFound />} />
      </Route>
    </Routes>
  );
}
