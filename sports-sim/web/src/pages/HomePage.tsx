import { Link } from 'react-router-dom';
import { SPORT_LABELS, type SportType } from '../types';
import '../styles/ui.css';

const SPORTS: SportType[] = ['soccer', 'basketball', 'baseball'];

export default function HomePage() {
  return (
    <div className="max-w-4xl mx-auto space-y-10">
      <section className="text-center space-y-3 pt-8">
        <h1 className="text-4xl font-extrabold tracking-tight">
          Multi-Sport Simulation Engine
        </h1>
        <p className="text-gray-400 max-w-xl mx-auto">
          Create, run, and stream realistic game simulations for Soccer,
          Basketball, and Baseball — with fatigue, injuries, weather, and
          momentum models.
        </p>
        <Link
          to="/simulate"
          className="inline-block mt-4 bg-blue-600 hover:bg-blue-500 text-white px-6 py-2.5 rounded-lg font-medium transition"
        >
          Start a Simulation
        </Link>
      </section>

      {/* ── sport cards ── */}
      <section className="grid grid-cols-1 sm:grid-cols-3 gap-6">
        {SPORTS.map((s) => (
          <Link
            key={s}
            to={`/simulate?sport=${s}`}
            className="group block rounded-xl border border-gray-800 bg-gray-900 p-6 hover:border-blue-500 transition"
          >
            <div
              className={`w-12 h-12 rounded-lg mb-4 flex items-center justify-center text-2xl font-bold text-white sport-color-${s}`}
            >
              {s[0]!.toUpperCase()}
            </div>
            <h3 className="text-lg font-semibold group-hover:text-blue-400 transition">
              {SPORT_LABELS[s]}
            </h3>
            <p className="text-sm text-gray-500 mt-1">
              {s === 'soccer' && '11 v 11 • 2 × 45 min • full pitch physics'}
              {s === 'basketball' && '5 v 5 • 4 × 12 min • shot clock & fouls'}
              {s === 'baseball' && '9 v 9 • 9 innings • at-bat driven events'}
            </p>
          </Link>
        ))}
      </section>

      {/* ── features overview ── */}
      <section className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-center text-sm">
        {[
          ['Fatigue', 'Stamina drains realistically over time'],
          ['Injuries', 'Probabilistic injury model with auto-substitution'],
          ['Weather', 'Rain, wind, heat, snow affect gameplay'],
          ['Momentum', 'Team morale shifts with key events'],
        ].map(([title, desc]) => (
          <div key={title} className="bg-gray-900 border border-gray-800 rounded-lg p-4">
            <div className="font-semibold text-gray-200">{title}</div>
            <div className="text-xs text-gray-500 mt-1">{desc}</div>
          </div>
        ))}
      </section>
    </div>
  );
}
