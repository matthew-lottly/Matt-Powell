import { Link } from 'react-router-dom';
import { SPORT_LABELS, SPORT_COLORS, type SportType } from '../types';
import '../styles/ui.css';

const SPORTS: SportType[] = ['soccer', 'basketball', 'baseball', 'football', 'hockey', 'tennis', 'golf', 'cricket', 'boxing', 'mma', 'racing'];

const SPORT_DESCRIPTIONS: Record<SportType, string> = {
  soccer: '11 v 11 • 2 × 45 min • full pitch physics',
  basketball: '5 v 5 • 4 × 12 min • shot clock & fouls',
  baseball: '9 v 9 • 9 innings • at-bat driven events',
  football: '11 v 11 • 4 × 15 min • drives, downs & turnovers',
  hockey: '6 v 6 • 3 × 20 min • power plays & saves',
  tennis: '1 v 1 • best of 3 sets • serve & rally',
  golf: '1 v 1 • 18 holes • stroke play',
  cricket: '11 v 11 • T20 format • overs & wickets',
  boxing: '1 v 1 • 12 rounds • punches & knockdowns',
  mma: '1 v 1 • 3 rounds • striking & grappling',
  racing: '1 v 1 • 50 laps • pit stops & overtakes',
};

export default function HomePage() {
  return (
    <div className="max-w-5xl mx-auto space-y-10 px-2 sm:px-4">
      <section className="text-center space-y-3 pt-8">
        <h1 className="text-3xl sm:text-4xl font-extrabold tracking-tight">
          Multi-Sport Simulation Engine
        </h1>
        <p className="text-gray-400 max-w-xl mx-auto text-sm sm:text-base">
          Create, run, and stream realistic game simulations across 11 sports —
          with fatigue, injuries, weather, momentum, coaches, and venue effects.
        </p>
        <Link
          to="/simulate"
          className="inline-block mt-4 bg-blue-600 hover:bg-blue-500 text-white px-6 py-2.5 rounded-lg font-medium transition"
        >
          Start a Simulation
        </Link>
      </section>

      {/* ── sport cards ── */}
      <section className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3 sm:gap-4">
        {SPORTS.map((s) => (
          <Link
            key={s}
            to={`/simulate?sport=${s}`}
            className="group block rounded-xl border border-gray-800 bg-gray-900 p-4 sm:p-5 hover:border-blue-500 transition"
          >
            <div
              className="w-10 h-10 sm:w-12 sm:h-12 rounded-lg mb-3 flex items-center justify-center text-xl sm:text-2xl font-bold text-white"
              style={{ backgroundColor: SPORT_COLORS[s] }}
            >
              {s === 'mma' ? 'M' : s[0]!.toUpperCase()}
            </div>
            <h3 className="text-sm sm:text-lg font-semibold group-hover:text-blue-400 transition">
              {SPORT_LABELS[s]}
            </h3>
            <p className="text-xs text-gray-500 mt-1 hidden sm:block">
              {SPORT_DESCRIPTIONS[s]}
            </p>
          </Link>
        ))}
      </section>

      {/* ── features overview ── */}
      <section className="grid grid-cols-2 sm:grid-cols-4 gap-3 sm:gap-4 text-center text-sm">
        {[
          ['Fatigue', 'Stamina drains realistically over time'],
          ['Injuries', 'Probabilistic injury model with auto-substitution'],
          ['Weather', 'Rain, wind, heat, snow affect gameplay'],
          ['Momentum', 'Team morale shifts with key events'],
          ['Coaches', 'Tactical style, play calling & motivation effects'],
          ['Venues', 'Real stadiums with altitude, noise & surface'],
          ['Sliders', 'Per-team strategy tuning before & during games'],
          ['Streaming', 'WebSocket real-time tick-by-tick game state'],
        ].map(([title, desc]) => (
          <div key={title} className="bg-gray-900 border border-gray-800 rounded-lg p-3 sm:p-4">
            <div className="font-semibold text-gray-200 text-xs sm:text-sm">{title}</div>
            <div className="text-xs text-gray-500 mt-1 hidden sm:block">{desc}</div>
          </div>
        ))}
      </section>
    </div>
  );
}
