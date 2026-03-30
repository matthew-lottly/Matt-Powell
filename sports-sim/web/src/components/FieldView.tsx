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

interface Props {
  sport: SportType;
  tick: StreamTick | null;
}

export default function FieldView({ sport, tick }: Props) {
  const common = { tick };

  return (
    <div className="bg-gray-900 border border-gray-800 rounded-xl p-4 flex items-center justify-center">
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
    </div>
  );
}
