import { Link } from 'react-router-dom';
import { SPORT_LABELS, type SportType } from '../types';
import { getSportPresentation } from '../sportPresentation';
import '../styles/ui.css';
import '../styles/sport-colors.css';

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
      <section className="text-center space-y-4 pt-8 pb-2 rounded-[28px] border border-white/8 bg-gradient-to-br from-slate-900 via-slate-950 to-slate-900 p-6 sm:p-10 shadow-[0_20px_70px_rgba(0,0,0,0.35)]">
        <div className="inline-flex items-center gap-2 rounded-full border border-blue-400/20 bg-blue-500/10 px-3 py-1 text-[11px] font-medium uppercase tracking-[0.22em] text-blue-200">
          11 sports · Real-time simulation · Tactical controls
        </div>
        <h1 className="text-3xl sm:text-5xl font-extrabold tracking-tight max-w-3xl mx-auto">
          Multi-Sport Simulation Engine
        </h1>
        <p className="text-slate-300 max-w-2xl mx-auto text-sm sm:text-base leading-6">
          Create, run, and stream realistic game simulations across 11 sports —
          with fatigue, injuries, weather, momentum, coaches, and venue effects.
        </p>
        <div className="flex flex-wrap items-center justify-center gap-3 pt-2">
          <Link
            to="/simulate"
            className="inline-block bg-blue-600 hover:bg-blue-500 text-white px-6 py-2.5 rounded-lg font-medium transition"
          >
            Start a Simulation
          </Link>
          <Link
            to="/leagues"
            className="inline-block border border-white/10 bg-white/5 hover:bg-white/10 text-slate-100 px-6 py-2.5 rounded-lg font-medium transition"
          >
            Browse Leagues
          </Link>
        </div>
      </section>

      {/* ── sport cards ── */}
      <section className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3 sm:gap-4">
        {SPORTS.map((s) => (
          <Link
            key={s}
            to={`/simulate?sport=${s}`}
            className="group relative overflow-hidden block rounded-2xl border border-white/8 bg-gradient-to-br from-slate-900 to-slate-950 p-4 sm:p-5 hover:border-blue-500/40 hover:-translate-y-0.5 transition"
          >
            <div className={`absolute inset-0 opacity-0 group-hover:opacity-100 transition bg-gradient-to-br ${getSportPresentation(s).heroGradient}`} />
            <div className={`relative z-10 w-10 h-10 sm:w-12 sm:h-12 rounded-lg mb-3 flex items-center justify-center text-xl sm:text-2xl font-bold text-white sport-bg-${s}`}>
              {s === 'mma' ? 'M' : s[0]!.toUpperCase()}
            </div>
            <div className="relative z-10 space-y-3">
              <div>
                <h3 className="text-sm sm:text-lg font-semibold group-hover:text-blue-300 transition">
                  {SPORT_LABELS[s]}
                </h3>
                <p className="text-xs text-slate-400 mt-1 hidden sm:block">
                  {SPORT_DESCRIPTIONS[s]}
                </p>
              </div>
              <div className="hidden sm:flex flex-wrap gap-2 text-[11px] text-slate-300">
                <span className={`rounded-full border px-2 py-1 ${getSportPresentation(s).accentBadge}`}>
                  {getSportPresentation(s).format}
                </span>
                <span className="rounded-full border border-white/10 bg-white/5 px-2 py-1">
                  {getSportPresentation(s).keyMoments[0]}
                </span>
              </div>
            </div>
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
          <div key={title} className="bg-slate-900/80 border border-white/8 rounded-xl p-3 sm:p-4 backdrop-blur-sm">
            <div className="font-semibold text-slate-100 text-xs sm:text-sm">{title}</div>
            <div className="text-xs text-slate-400 mt-1 hidden sm:block">{desc}</div>
          </div>
        ))}
      </section>
    </div>
  );
}
