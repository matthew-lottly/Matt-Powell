import type { SportType, StreamTick } from '../types';
import SoccerField from './fields/SoccerField';
import BasketballCourt from './fields/BasketballCourt';
import BaseballDiamond from './fields/BaseballDiamond';
import FootballField from './fields/FootballField';
import HockeyRink from './fields/HockeyRink';
import TennisCourt from './fields/TennisCourt';
import GolfCourse from './fields/GolfCourse';
import CricketField from './fields/CricketField';
import BoxingRing from './fields/BoxingRing';
import OctagonView from './fields/Octagon';
import RaceTrack from './fields/RaceTrack';
import HeatmapOverlay from './HeatmapOverlay';
import { getSportPresentation } from '../sportPresentation';
import SportFieldOverlay from './SportFieldOverlay';

interface Props {
  sport: SportType;
  tick: StreamTick | null;
  showHeatmap?: boolean;
  heatmapTeam?: 'home' | 'away' | null;
}

export default function FieldView({ sport, tick, showHeatmap = false, heatmapTeam = null }: Props) {
  const common = { tick };
  const presentation = getSportPresentation(sport);
  const latestEvent = tick?.events[tick.events.length - 1] ?? null;

  return (
    <div className={`rounded-[24px] border border-white/8 bg-gradient-to-br ${presentation.fieldShell} overflow-hidden ${presentation.eventGlow}`}>
      <div className="border-b border-white/8 px-4 py-3 sm:px-5 bg-black/10">
        <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <div className={`text-xs uppercase tracking-[0.2em] ${presentation.accentText}`}>{presentation.label} Surface</div>
            <div className="text-sm text-slate-300 mt-1">{presentation.atmosphere}</div>
          </div>
          <div className="rounded-full border border-white/10 bg-white/5 px-3 py-1 text-xs text-slate-300">
            {latestEvent?.description ?? presentation.emptyState}
          </div>
        </div>
      </div>
      <div className="p-4">
        <div className="relative flex min-h-[280px] sm:min-h-[340px] items-center justify-center overflow-hidden rounded-[20px] border border-white/6 bg-black/10">
          {sport === 'soccer' && <SoccerField {...common} />}
          {sport === 'basketball' && <BasketballCourt {...common} />}
          {sport === 'baseball' && <BaseballDiamond {...common} />}
          {sport === 'football' && <FootballField {...common} />}
          {sport === 'hockey' && <HockeyRink {...common} />}
          {sport === 'tennis' && <TennisCourt {...common} />}
          {sport === 'golf' && <GolfCourse {...common} />}
          {sport === 'cricket' && <CricketField {...common} />}
          {sport === 'boxing' && <BoxingRing {...common} />}
          {sport === 'mma' && <OctagonView {...common} />}
          {sport === 'racing' && <RaceTrack {...common} />}
          {showHeatmap && <HeatmapOverlay gameId={tick?.game_id ?? null} team={heatmapTeam} />}
          <SportFieldOverlay sport={sport} tick={tick} />
        </div>
      </div>
      <div className="border-t border-white/8 px-4 py-3 sm:px-5">
        <div className="text-[11px] uppercase tracking-[0.2em] text-slate-500 mb-2">What matters here</div>
        <div className="flex flex-wrap gap-2">
          {presentation.keyMoments.map((item) => (
            <span key={item} className={`rounded-full border px-3 py-1 text-xs ${presentation.accentBadge}`}>
              {item}
            </span>
          ))}
        </div>
      </div>
    </div>
  );
}
