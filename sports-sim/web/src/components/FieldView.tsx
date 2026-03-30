import type { SportType, StreamTick } from '../types';
import SoccerField from './fields/SoccerField';
import BasketballCourt from './fields/BasketballCourt';
import BaseballDiamond from './fields/BaseballDiamond';

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
    </div>
  );
}
