import type { StreamTick, SportType } from '../types';
import { SPORT_LABELS } from '../types';
import { getSportPresentation } from '../sportPresentation';
import { formatSportClock, formatSportPeriod } from '../sportUi';

interface Props {
  tick: StreamTick | null;
  sport: SportType;
}

export default function Scoreboard({ tick, sport }: Props) {
  const presentation = getSportPresentation(sport);

  if (!tick) {
    return (
      <div className={`rounded-2xl border border-white/8 bg-gradient-to-br ${presentation.accentPanel} from-slate-900 to-slate-950 p-6 text-center text-slate-400`}>
        <div className="text-[11px] uppercase tracking-[0.22em] text-slate-500">{presentation.statusVerb}</div>
        <div className="mt-2 text-lg text-slate-100">{presentation.emptyState}</div>
        <div className="mt-2 text-sm">
          Press <span className={`font-semibold ${presentation.accentText}`}>Start</span> to begin.
        </div>
      </div>
    );
  }

  const periodLabel = formatSportPeriod(sport, tick.period);
  const clockLabel = formatSportClock(sport, tick.clock);

  return (
    <section aria-label="Scoreboard" className={`rounded-2xl border border-white/8 bg-gradient-to-br ${presentation.accentPanel} p-4 ring-1 ${presentation.accentRing}`}>
      <div className="flex flex-wrap items-center justify-between gap-2 text-xs mb-3">
        <div className="text-slate-400">
          {SPORT_LABELS[sport]} · {periodLabel} · {clockLabel}
        </div>
        <div className={`rounded-full border px-2.5 py-1 ${presentation.accentBadge}`}>
          {presentation.scoreLabel}
        </div>
      </div>
      <div className="flex items-center justify-center gap-4 text-3xl font-extrabold tabular-nums" aria-live="polite" role="status">
        <div className="text-right">
          <div className="text-xs text-blue-200 font-normal uppercase tracking-[0.18em]">{tick.home_team}</div>
          <span className="text-blue-400">{tick.home_score}</span>
        </div>
        <span className="text-slate-600" aria-hidden="true">–</span>
        <div className="text-left">
          <div className="text-xs text-red-200 font-normal uppercase tracking-[0.18em]">{tick.away_team}</div>
          <span className="text-red-400">{tick.away_score}</span>
        </div>
      </div>
      <div className="mt-3 grid grid-cols-3 gap-2 text-center text-[11px] text-slate-400">
        <div className="rounded-xl border border-white/6 bg-black/10 px-2 py-2">
          <div className="uppercase tracking-[0.16em] text-slate-500">Format</div>
          <div className="mt-1 text-slate-200">{presentation.format}</div>
        </div>
        <div className="rounded-xl border border-white/6 bg-black/10 px-2 py-2">
          <div className="uppercase tracking-[0.16em] text-slate-500">Rhythm</div>
          <div className="mt-1 text-slate-200">{presentation.rhythm}</div>
        </div>
        <div className="rounded-xl border border-white/6 bg-black/10 px-2 py-2">
          <div className="uppercase tracking-[0.16em] text-slate-500">Status</div>
          <div className="mt-1 text-slate-200">{tick.is_finished ? 'Final' : 'Live'}</div>
        </div>
      </div>
      {tick.is_finished && (
        <div className="text-center mt-3 text-green-400 text-xs font-semibold uppercase tracking-wider" role="status" aria-live="polite">
          Final
        </div>
      )}
    </section>
  );
}
