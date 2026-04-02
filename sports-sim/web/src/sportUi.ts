import { getSportPresentation } from './sportPresentation';
import type { SportType, StreamTick } from './types';

export type PlayerAttributeKey =
  | 'speed'
  | 'strength'
  | 'accuracy'
  | 'endurance'
  | 'skill'
  | 'decision_making'
  | 'aggression'
  | 'composure'
  | 'awareness'
  | 'leadership'
  | 'clutch'
  | 'durability';

export interface SportStatColumn {
  key: PlayerAttributeKey;
  label: string;
  shortLabel: string;
}

export interface SportRosterLabels {
  starters: string;
  bench: string;
  starterMetric: string;
  benchMetric: string;
}

export interface SportConfigLabels {
  panelTitle: string;
  sportLabel: string;
  leagueLabel: string;
  homeLabel: string;
  awayLabel: string;
  venueLabel: string;
  weatherLabel: string;
  slidersLabel: string;
}

export interface SportInsightCard {
  label: string;
  value: string;
  detail: string;
}

interface SportEventItem {
  type: string;
  time: number;
  description: string;
  period: number;
}

export const LEAGUE_SPORT: Record<string, SportType> = {
  nfl: 'football',
  nba: 'basketball',
  mlb: 'baseball',
  nhl: 'hockey',
  mls: 'soccer',
  epl: 'soccer',
  ncaasoc: 'soccer',
  npb: 'baseball',
  khl: 'hockey',
  euro: 'basketball',
  ipl: 'cricket',
};

export function humanizeToken(value: string): string {
  return value
    .replace(/_/g, ' ')
    .replace(/\b\w/g, (match) => match.toUpperCase());
}

export function formatSimulationScore(sport: SportType, home: number, away: number): string {
  const label = getSportPresentation(sport).scoreLabel.toLowerCase();
  return `${home} - ${away} ${label}`;
}

export function formatSportPeriod(sport: SportType, period: number): string {
  if (sport === 'soccer') return `Half ${period}`;
  if (sport === 'basketball' || sport === 'football') return `Q${period}`;
  if (sport === 'hockey') return `Period ${period}`;
  if (sport === 'tennis') return `Set ${period}`;
  if (sport === 'golf') return `Hole ${period}`;
  if (sport === 'cricket') return `Over ${period}`;
  if (sport === 'boxing' || sport === 'mma') return `Round ${period}`;
  if (sport === 'racing') return `Lap ${period}`;
  return `Inning ${period}`;
}

export function formatSportClock(sport: SportType, clock: number): string {
  const value = clock.toFixed(1);

  if (sport === 'soccer') return `${value} match min`;
  if (sport === 'basketball') return `${value} game min`;
  if (sport === 'baseball') return `${value} game min`;
  if (sport === 'football') return `${value} game min`;
  if (sport === 'hockey') return `${value} ice min`;
  if (sport === 'tennis') return `${value} match min`;
  if (sport === 'golf') return `${value} round min`;
  if (sport === 'cricket') return `${value} innings min`;
  if (sport === 'boxing') return `${value} fight min`;
  if (sport === 'mma') return `${value} fight min`;
  return `${value} race min`;
}

export function getSportMomentumLabel(sport: SportType): string {
  if (sport === 'soccer') return 'Territory Swing';
  if (sport === 'basketball') return 'Run Pressure';
  if (sport === 'baseball') return 'Game Pressure';
  if (sport === 'football') return 'Drive Control';
  if (sport === 'hockey') return 'Ice Tilt';
  if (sport === 'tennis') return 'Match Control';
  if (sport === 'golf') return 'Round Pressure';
  if (sport === 'cricket') return 'Chase Pressure';
  if (sport === 'boxing') return 'Damage Flow';
  if (sport === 'mma') return 'Fight Control';
  return 'Race Control';
}

export function getSportConfigLabels(sport: SportType): SportConfigLabels {
  if (sport === 'tennis') {
    return {
      panelTitle: 'Match Setup',
      sportLabel: 'Discipline',
      leagueLabel: 'Tour / League',
      homeLabel: 'Player A',
      awayLabel: 'Player B',
      venueLabel: 'Court',
      weatherLabel: 'Conditions',
      slidersLabel: 'Match Plan Sliders',
    };
  }
  if (sport === 'golf') {
    return {
      panelTitle: 'Round Setup',
      sportLabel: 'Discipline',
      leagueLabel: 'Tour / Event',
      homeLabel: 'Golfer A',
      awayLabel: 'Golfer B',
      venueLabel: 'Course',
      weatherLabel: 'Course Conditions',
      slidersLabel: 'Round Strategy Sliders',
    };
  }
  if (sport === 'boxing') {
    return {
      panelTitle: 'Fight Setup',
      sportLabel: 'Discipline',
      leagueLabel: 'Promotion / League',
      homeLabel: 'Fighter A',
      awayLabel: 'Fighter B',
      venueLabel: 'Arena',
      weatherLabel: 'Fight Conditions',
      slidersLabel: 'Fight Plan Sliders',
    };
  }
  if (sport === 'mma') {
    return {
      panelTitle: 'Fight Setup',
      sportLabel: 'Discipline',
      leagueLabel: 'Promotion / League',
      homeLabel: 'Fighter A',
      awayLabel: 'Fighter B',
      venueLabel: 'Octagon Venue',
      weatherLabel: 'Fight Conditions',
      slidersLabel: 'Fight Plan Sliders',
    };
  }
  if (sport === 'racing') {
    return {
      panelTitle: 'Race Setup',
      sportLabel: 'Discipline',
      leagueLabel: 'Series / Grid',
      homeLabel: 'Driver A',
      awayLabel: 'Driver B',
      venueLabel: 'Track',
      weatherLabel: 'Track Conditions',
      slidersLabel: 'Race Strategy Sliders',
    };
  }
  if (sport === 'hockey') {
    return {
      panelTitle: 'Game Setup',
      sportLabel: 'Sport',
      leagueLabel: 'League',
      homeLabel: 'Home Club',
      awayLabel: 'Away Club',
      venueLabel: 'Rink',
      weatherLabel: 'Conditions',
      slidersLabel: 'Bench Strategy Sliders',
    };
  }
  if (sport === 'cricket') {
    return {
      panelTitle: 'Match Setup',
      sportLabel: 'Sport',
      leagueLabel: 'League / Competition',
      homeLabel: 'Batting Side',
      awayLabel: 'Bowling Side',
      venueLabel: 'Ground',
      weatherLabel: 'Conditions',
      slidersLabel: 'Match Strategy Sliders',
    };
  }
  if (sport === 'baseball') {
    return {
      panelTitle: 'Game Setup',
      sportLabel: 'Sport',
      leagueLabel: 'League',
      homeLabel: 'Home Club',
      awayLabel: 'Away Club',
      venueLabel: 'Ballpark',
      weatherLabel: 'Game Conditions',
      slidersLabel: 'Game Plan Sliders',
    };
  }
  if (sport === 'football') {
    return {
      panelTitle: 'Game Setup',
      sportLabel: 'Sport',
      leagueLabel: 'League',
      homeLabel: 'Home Side',
      awayLabel: 'Away Side',
      venueLabel: 'Stadium',
      weatherLabel: 'Game Conditions',
      slidersLabel: 'Coordinator Sliders',
    };
  }
  if (sport === 'basketball') {
    return {
      panelTitle: 'Game Setup',
      sportLabel: 'Sport',
      leagueLabel: 'League',
      homeLabel: 'Home Side',
      awayLabel: 'Away Side',
      venueLabel: 'Arena',
      weatherLabel: 'Arena Conditions',
      slidersLabel: 'Rotation Sliders',
    };
  }
  return {
    panelTitle: 'Match Setup',
    sportLabel: 'Sport',
    leagueLabel: 'League',
    homeLabel: 'Home Side',
    awayLabel: 'Away Side',
    venueLabel: 'Venue',
    weatherLabel: 'Conditions',
    slidersLabel: 'Strategy Sliders',
  };
}

export function getSportRosterLabels(sport: SportType): SportRosterLabels {
  if (sport === 'soccer') {
    return {
      starters: 'Starting XI',
      bench: 'Bench',
      starterMetric: 'Lineup Rating',
      benchMetric: 'Bench Rating',
    };
  }
  if (sport === 'basketball') {
    return {
      starters: 'Starting Five',
      bench: 'Rotation',
      starterMetric: 'Starting Five',
      benchMetric: 'Second Unit',
    };
  }
  if (sport === 'baseball') {
    return {
      starters: 'Starting Nine',
      bench: 'Bench & Bullpen',
      starterMetric: 'Starting Nine',
      benchMetric: 'Depth Mix',
    };
  }
  if (sport === 'football') {
    return {
      starters: 'Depth Chart Core',
      bench: 'Support Unit',
      starterMetric: 'Core Unit',
      benchMetric: 'Support Unit',
    };
  }
  if (sport === 'hockey') {
    return {
      starters: 'Starting Six',
      bench: 'Bench & Goalies',
      starterMetric: 'Top Six',
      benchMetric: 'Depth Lines',
    };
  }
  if (sport === 'cricket') {
    return {
      starters: 'Playing XI',
      bench: 'Reserve Group',
      starterMetric: 'Playing XI',
      benchMetric: 'Reserve Group',
    };
  }
  return {
    starters: 'Active Squad',
    bench: 'Bench',
    starterMetric: 'Starter Rating',
    benchMetric: 'Bench Depth',
  };
}

export function getSportRosterColumns(sport: SportType): SportStatColumn[] {
  if (sport === 'soccer') {
    return [
      { key: 'speed', label: 'Burst', shortLabel: 'BST' },
      { key: 'skill', label: 'Touch', shortLabel: 'TCH' },
      { key: 'accuracy', label: 'Finishing', shortLabel: 'FIN' },
      { key: 'endurance', label: 'Engine', shortLabel: 'ENG' },
      { key: 'decision_making', label: 'Vision', shortLabel: 'VIS' },
    ];
  }
  if (sport === 'basketball') {
    return [
      { key: 'speed', label: 'Burst', shortLabel: 'BST' },
      { key: 'accuracy', label: 'Shotmaking', shortLabel: 'SHO' },
      { key: 'skill', label: 'Handle', shortLabel: 'HND' },
      { key: 'decision_making', label: 'Read', shortLabel: 'READ' },
      { key: 'clutch', label: 'Closing', shortLabel: 'CLS' },
    ];
  }
  if (sport === 'baseball') {
    return [
      { key: 'accuracy', label: 'Contact', shortLabel: 'CON' },
      { key: 'skill', label: 'Power', shortLabel: 'POW' },
      { key: 'decision_making', label: 'Plate IQ', shortLabel: 'IQ' },
      { key: 'composure', label: 'Calm', shortLabel: 'CLM' },
      { key: 'clutch', label: 'Clutch', shortLabel: 'CLT' },
    ];
  }
  if (sport === 'football') {
    return [
      { key: 'strength', label: 'Power', shortLabel: 'POW' },
      { key: 'speed', label: 'Burst', shortLabel: 'BST' },
      { key: 'accuracy', label: 'Execution', shortLabel: 'EXE' },
      { key: 'decision_making', label: 'Read', shortLabel: 'READ' },
      { key: 'endurance', label: 'Conditioning', shortLabel: 'COND' },
    ];
  }
  if (sport === 'hockey') {
    return [
      { key: 'speed', label: 'Skating', shortLabel: 'SKT' },
      { key: 'accuracy', label: 'Shot', shortLabel: 'SHT' },
      { key: 'skill', label: 'Hands', shortLabel: 'HND' },
      { key: 'awareness', label: 'Read', shortLabel: 'READ' },
      { key: 'composure', label: 'Calm', shortLabel: 'CLM' },
    ];
  }
  if (sport === 'tennis') {
    return [
      { key: 'accuracy', label: 'Placement', shortLabel: 'PLC' },
      { key: 'skill', label: 'Technique', shortLabel: 'TEC' },
      { key: 'speed', label: 'Court Speed', shortLabel: 'CRT' },
      { key: 'composure', label: 'Nerve', shortLabel: 'NRV' },
      { key: 'endurance', label: 'Stamina', shortLabel: 'STA' },
    ];
  }
  if (sport === 'golf') {
    return [
      { key: 'accuracy', label: 'Control', shortLabel: 'CTL' },
      { key: 'skill', label: 'Shotmaking', shortLabel: 'SHO' },
      { key: 'decision_making', label: 'Course IQ', shortLabel: 'IQ' },
      { key: 'composure', label: 'Calm', shortLabel: 'CLM' },
      { key: 'clutch', label: 'Pressure', shortLabel: 'PRS' },
    ];
  }
  if (sport === 'cricket') {
    return [
      { key: 'accuracy', label: 'Timing', shortLabel: 'TIM' },
      { key: 'skill', label: 'Technique', shortLabel: 'TEC' },
      { key: 'decision_making', label: 'Shot Select', shortLabel: 'SEL' },
      { key: 'endurance', label: 'Stamina', shortLabel: 'STA' },
      { key: 'clutch', label: 'Finish', shortLabel: 'FIN' },
    ];
  }
  if (sport === 'boxing') {
    return [
      { key: 'strength', label: 'Power', shortLabel: 'POW' },
      { key: 'speed', label: 'Hands', shortLabel: 'HND' },
      { key: 'aggression', label: 'Pressure', shortLabel: 'PRS' },
      { key: 'composure', label: 'Defense', shortLabel: 'DEF' },
      { key: 'endurance', label: 'Tank', shortLabel: 'TNK' },
    ];
  }
  if (sport === 'mma') {
    return [
      { key: 'strength', label: 'Control', shortLabel: 'CTL' },
      { key: 'skill', label: 'Technique', shortLabel: 'TEC' },
      { key: 'aggression', label: 'Pressure', shortLabel: 'PRS' },
      { key: 'decision_making', label: 'Fight IQ', shortLabel: 'IQ' },
      { key: 'endurance', label: 'Tank', shortLabel: 'TNK' },
    ];
  }
  return [
    { key: 'speed', label: 'Pace', shortLabel: 'PAC' },
    { key: 'decision_making', label: 'Read', shortLabel: 'READ' },
    { key: 'composure', label: 'Control', shortLabel: 'CTL' },
    { key: 'endurance', label: 'Endurance', shortLabel: 'END' },
    { key: 'clutch', label: 'Finish', shortLabel: 'FIN' },
  ];
}

export function getSportAttributeLabel(sport: SportType, key: string): string {
  const labels: Partial<Record<SportType, Partial<Record<PlayerAttributeKey, string>>>> = {
    soccer: {
      speed: 'Burst',
      strength: 'Physicality',
      accuracy: 'Finishing',
      endurance: 'Engine',
      skill: 'Touch',
      decision_making: 'Vision',
      aggression: 'Press Rate',
      composure: 'Composure',
      awareness: 'Positioning',
      leadership: 'Leadership',
      clutch: 'Big Moments',
      durability: 'Durability',
    },
    basketball: {
      speed: 'Burst',
      strength: 'Frame',
      accuracy: 'Shotmaking',
      endurance: 'Motor',
      skill: 'Handle',
      decision_making: 'Read',
      aggression: 'Rim Pressure',
      composure: 'Poise',
      awareness: 'Help Defense',
      leadership: 'Locker Room',
      clutch: 'Closing',
      durability: 'Availability',
    },
    baseball: {
      speed: 'Basepath Speed',
      strength: 'Power Base',
      accuracy: 'Contact',
      endurance: 'Workload',
      skill: 'Power',
      decision_making: 'Plate IQ',
      aggression: 'Attack Rate',
      composure: 'At-Bat Calm',
      awareness: 'Field Awareness',
      leadership: 'Clubhouse',
      clutch: 'RISP Nerve',
      durability: 'Availability',
    },
    football: {
      speed: 'Burst',
      strength: 'Power',
      accuracy: 'Execution',
      endurance: 'Conditioning',
      skill: 'Technique',
      decision_making: 'Read',
      aggression: 'Contact',
      composure: 'Pocket Calm',
      awareness: 'Field Vision',
      leadership: 'Command',
      clutch: 'Late Drives',
      durability: 'Toughness',
    },
    hockey: {
      speed: 'Skating',
      strength: 'Board Play',
      accuracy: 'Shot',
      endurance: 'Shift Tank',
      skill: 'Hands',
      decision_making: 'Read',
      aggression: 'Forecheck',
      composure: 'Calm',
      awareness: 'Positioning',
      leadership: 'Room Presence',
      clutch: 'Finishing Touch',
      durability: 'Durability',
    },
  };

  return labels[sport]?.[key as PlayerAttributeKey] ?? humanizeToken(key);
}

function countEvents(events: SportEventItem[], types: string[]): number {
  return events.filter((event) => types.includes(event.type)).length;
}

function edgeLabel(delta: number, homeText: string, awayText: string, balancedText: string): string {
  if (delta > 0.1) return homeText;
  if (delta < -0.1) return awayText;
  return balancedText;
}

export function getSportInsightCards(
  sport: SportType,
  tick: StreamTick | null,
  events: SportEventItem[],
): SportInsightCard[] {
  if (!tick) {
    const presentation = getSportPresentation(sport);
    return [
      { label: 'Format', value: presentation.format, detail: presentation.headline },
      { label: 'Rhythm', value: presentation.rhythm, detail: presentation.atmosphere },
      { label: 'Key Moment', value: presentation.keyMoments[0] ?? presentation.label, detail: presentation.emptyState },
      { label: 'Status', value: presentation.statusVerb, detail: presentation.emptyState },
    ];
  }

  const delta = tick.home_momentum - tick.away_momentum;
  const periodLabel = formatSportPeriod(sport, tick.period);
  const clockLabel = formatSportClock(sport, tick.clock);

  if (sport === 'soccer') {
    const ss = tick.sport_state ?? {};
    const possession = (ss.possession as string) || 'Contested';
    const homeShots = (ss.home_shots as number) ?? countEvents(events, ['shot']);
    const awayShots = (ss.away_shots as number) ?? 0;
    const homeYellows = (ss.home_yellows as number) ?? 0;
    const awayYellows = (ss.away_yellows as number) ?? 0;
    const homeReds = (ss.home_reds as number) ?? 0;
    const awayReds = (ss.away_reds as number) ?? 0;
    const homeCorners = (ss.home_corners as number) ?? 0;
    const awayCorners = (ss.away_corners as number) ?? 0;
    return [
      { label: 'Possession', value: possession, detail: `${Math.round(Math.abs(delta) * 100)}% pressure edge` },
      { label: 'Shots', value: `${homeShots} - ${awayShots}`, detail: `${homeCorners + awayCorners} corners won` },
      { label: 'Discipline', value: `${homeYellows + awayYellows}Y ${homeReds + awayReds}R`, detail: `${homeYellows}/${awayYellows} yellows · ${homeReds}/${awayReds} reds` },
      { label: 'Match Phase', value: periodLabel, detail: clockLabel },
    ];
  }
  if (sport === 'basketball') {
    const ss = tick.sport_state ?? {};
    const possession = (ss.possession as string) || '';
    const shotClock = (ss.shot_clock as number) ?? 0;
    const homeFG = (ss.home_fg_att as number) ?? countEvents(events, ['shot']);
    const awayFG = (ss.away_fg_att as number) ?? 0;
    const homeReb = (ss.home_rebounds as number) ?? 0;
    const awayReb = (ss.away_rebounds as number) ?? 0;
    const homeTO = (ss.home_turnovers as number) ?? 0;
    const awayTO = (ss.away_turnovers as number) ?? 0;
    const homeFouls = (ss.home_fouls as number) ?? 0;
    const awayFouls = (ss.away_fouls as number) ?? 0;
    return [
      { label: 'Ball', value: possession || 'Transition', detail: `Shot clock: ${shotClock.toFixed(1)}s` },
      { label: 'FG Attempts', value: `${homeFG} - ${awayFG}`, detail: `Rebounds: ${homeReb} - ${awayReb}` },
      { label: 'Turnovers', value: `${homeTO} - ${awayTO}`, detail: `Fouls: ${homeFouls} - ${awayFouls}` },
      { label: 'Game Phase', value: periodLabel, detail: clockLabel },
    ];
  }
  if (sport === 'baseball') {
    const ss = tick.sport_state ?? {};
    const outs = (ss.outs as number) ?? 0;
    const bases = (ss.bases as boolean[]) ?? [false, false, false];
    const half = (ss.inning_half as string) ?? 'top';
    const homeHits = (ss.home_hits as number) ?? countEvents(events, ['hit']);
    const awayHits = (ss.away_hits as number) ?? 0;
    const homeK = (ss.home_strikeouts as number) ?? 0;
    const awayK = (ss.away_strikeouts as number) ?? 0;
    const runners = bases.filter(Boolean).length;
    const basesStr = bases.map((b: boolean, i: number) => b ? ['1B', '2B', '3B'][i] : '_').join(' ');
    return [
      { label: 'Count', value: `${outs} Out${outs !== 1 ? 's' : ''}`, detail: `${half.charAt(0).toUpperCase() + half.slice(1)} of ${tick.period}` },
      { label: 'Bases', value: `${runners} On`, detail: basesStr },
      { label: 'Hits', value: `${homeHits} - ${awayHits}`, detail: `K: ${homeK} - ${awayK}` },
      { label: 'Inning', value: periodLabel, detail: clockLabel },
    ];
  }
  if (sport === 'football') {
    const ss = tick.sport_state ?? {};
    const down = (ss.down as number) ?? 0;
    const ytg = (ss.yards_to_go as number) ?? 0;
    const ballOn = (ss.ball_on as number) ?? 0;
    const redZone = (ss.red_zone as boolean) ?? false;
    const homeYards = (ss.home_total_yards as number) ?? 0;
    const awayYards = (ss.away_total_yards as number) ?? 0;
    const homeTO = (ss.home_turnovers as number) ?? 0;
    const awayTO = (ss.away_turnovers as number) ?? 0;
    const homeSacks = (ss.home_sacks as number) ?? 0;
    const awaySacks = (ss.away_sacks as number) ?? 0;
    const downStr = down > 0 ? `${down}${['st','nd','rd','th'][Math.min(down-1,3)]} & ${Math.round(ytg)}` : 'Kickoff';
    return [
      { label: 'Down & Distance', value: downStr, detail: `Ball on ${Math.round(ballOn)}-yard line${redZone ? ' · RED ZONE' : ''}` },
      { label: 'Total Yards', value: `${homeYards} - ${awayYards}`, detail: `Sacks: ${homeSacks} - ${awaySacks}` },
      { label: 'Turnovers', value: `${homeTO} - ${awayTO}`, detail: `Penalties: ${(ss.home_penalties as number) ?? 0} - ${(ss.away_penalties as number) ?? 0}` },
      { label: 'Game Script', value: edgeLabel(delta, 'Home Dictating', 'Away Dictating', 'Even Script'), detail: `${periodLabel} · ${clockLabel}` },
    ];
  }
  if (sport === 'hockey') {
    const ss = tick.sport_state ?? {};
    const homePP = (ss.home_power_play as boolean) ?? false;
    const awayPP = (ss.away_power_play as boolean) ?? false;
    const homeShots = (ss.home_shots as number) ?? countEvents(events, ['shot']);
    const awayShots = (ss.away_shots as number) ?? 0;
    const homeSaves = (ss.home_saves as number) ?? 0;
    const awaySaves = (ss.away_saves as number) ?? 0;
    const homeFO = (ss.home_faceoff_wins as number) ?? 0;
    const awayFO = (ss.away_faceoff_wins as number) ?? 0;
    const ppStatus = homePP ? 'Home PP' : awayPP ? 'Away PP' : 'Even Strength';
    return [
      { label: 'Strength', value: ppStatus, detail: homePP || awayPP ? 'Power play active' : 'Five on five' },
      { label: 'Shots', value: `${homeShots} - ${awayShots}`, detail: `Saves: ${homeSaves} - ${awaySaves}` },
      { label: 'Faceoffs', value: `${homeFO} - ${awayFO}`, detail: `Win %: ${(homeFO + awayFO) > 0 ? Math.round(homeFO / (homeFO + awayFO) * 100) : 50}%` },
      { label: 'Ice State', value: periodLabel, detail: clockLabel },
    ];
  }
  if (sport === 'tennis') {
    const ss = tick.sport_state ?? {};
    const p1Pts = (ss.p1_point_label as string) ?? '0';
    const p2Pts = (ss.p2_point_label as string) ?? '0';
    const p1Games = (ss.p1_games as number) ?? 0;
    const p2Games = (ss.p2_games as number) ?? 0;
    const p1Sets = (ss.p1_sets as number) ?? 0;
    const p2Sets = (ss.p2_sets as number) ?? 0;
    const serving = (ss.serving_p1 as boolean) ?? true;
    const p1Aces = (ss.p1_aces as number) ?? 0;
    const p2Aces = (ss.p2_aces as number) ?? 0;
    const p1W = (ss.p1_winners as number) ?? 0;
    const p2W = (ss.p2_winners as number) ?? 0;
    const p1UE = (ss.p1_unforced_errors as number) ?? 0;
    const p2UE = (ss.p2_unforced_errors as number) ?? 0;
    return [
      { label: 'Game Score', value: `${p1Pts} - ${p2Pts}`, detail: `${serving ? 'P1' : 'P2'} serving · Games: ${p1Games}-${p2Games}` },
      { label: 'Sets', value: `${p1Sets} - ${p2Sets}`, detail: `Aces: ${p1Aces} - ${p2Aces}` },
      { label: 'Shot Quality', value: `W: ${p1W}-${p2W}`, detail: `UE: ${p1UE} - ${p2UE}` },
      { label: 'Match State', value: periodLabel, detail: clockLabel },
    ];
  }
  if (sport === 'golf') {
    const ss = tick.sport_state ?? {};
    const hole = (ss.current_hole as number) ?? 0;
    const p1Par = (ss.p1_relative_to_par as number) ?? 0;
    const p2Par = (ss.p2_relative_to_par as number) ?? 0;
    const p1Strokes = (ss.p1_total_strokes as number) ?? 0;
    const p2Strokes = (ss.p2_total_strokes as number) ?? 0;
    const p1Birdies = (ss.p1_birdies as number) ?? 0;
    const p2Birdies = (ss.p2_birdies as number) ?? 0;
    const fmtPar = (n: number) => n === 0 ? 'E' : n > 0 ? `+${n}` : `${n}`;
    return [
      { label: 'Hole', value: `${hole} / 18`, detail: `Strokes: ${p1Strokes} - ${p2Strokes}` },
      { label: 'P1 Score', value: fmtPar(p1Par), detail: `${p1Birdies} birdie${p1Birdies !== 1 ? 's' : ''}` },
      { label: 'P2 Score', value: fmtPar(p2Par), detail: `${p2Birdies} birdie${p2Birdies !== 1 ? 's' : ''}` },
      { label: 'Round State', value: periodLabel, detail: clockLabel },
    ];
  }
  if (sport === 'cricket') {
    const ss = tick.sport_state ?? {};
    const wickets = (ss.wickets as number) ?? 0;
    const overDisplay = (ss.over_display as string) ?? `${(ss.overs as number) ?? 0}.${(ss.balls_in_over as number) ?? 0}`;
    const fours = (ss.boundaries_four as number) ?? countEvents(events, ['boundary_four']);
    const sixes = (ss.sixes as number) ?? countEvents(events, ['six']);
    const extras = (ss.extras as number) ?? 0;
    const maidens = (ss.maiden_overs as number) ?? 0;
    return [
      { label: 'Wickets', value: `${wickets} / 10`, detail: `Overs: ${overDisplay}` },
      { label: 'Boundaries', value: `${fours} × 4  ${sixes} × 6`, detail: `${fours * 4 + sixes * 6} runs from boundaries` },
      { label: 'Bowling', value: `${maidens} maidens`, detail: `${extras} extras conceded` },
      { label: 'Over State', value: periodLabel, detail: clockLabel },
    ];
  }
  if (sport === 'boxing') {
    const ss = tick.sport_state ?? {};
    const p1Health = (ss.p1_health as number) ?? 100;
    const p2Health = (ss.p2_health as number) ?? 100;
    const p1KD = (ss.p1_knockdowns as number) ?? 0;
    const p2KD = (ss.p2_knockdowns as number) ?? 0;
    const p1Total = (ss.p1_total_score as number) ?? 0;
    const p2Total = (ss.p2_total_score as number) ?? 0;
    const p1Punches = (ss.p1_punches as number) ?? 0;
    const p2Punches = (ss.p2_punches as number) ?? 0;
    return [
      { label: 'Health', value: `${Math.round(p1Health)}% / ${Math.round(p2Health)}%`, detail: `Fighter A / Fighter B` },
      { label: 'Scorecard', value: `${p1Total} - ${p2Total}`, detail: `KD: ${p1KD} - ${p2KD}` },
      { label: 'Output', value: `${p1Punches} - ${p2Punches}`, detail: 'punches landed' },
      { label: 'Round State', value: periodLabel, detail: clockLabel },
    ];
  }
  if (sport === 'mma') {
    const ss = tick.sport_state ?? {};
    const p1Health = (ss.p1_health as number) ?? 100;
    const p2Health = (ss.p2_health as number) ?? 100;
    const onGround = (ss.on_ground as boolean) ?? false;
    const p1Total = (ss.p1_total_score as number) ?? 0;
    const p2Total = (ss.p2_total_score as number) ?? 0;
    const p1Strikes = (ss.p1_strikes as number) ?? 0;
    const p2Strikes = (ss.p2_strikes as number) ?? 0;
    const p1TD = (ss.p1_takedowns as number) ?? 0;
    const p2TD = (ss.p2_takedowns as number) ?? 0;
    return [
      { label: 'Health', value: `${Math.round(p1Health)}% / ${Math.round(p2Health)}%`, detail: onGround ? 'On the ground' : 'Standing' },
      { label: 'Scorecard', value: `${p1Total} - ${p2Total}`, detail: `Strikes: ${p1Strikes} - ${p2Strikes}` },
      { label: 'Grappling', value: `TD: ${p1TD} - ${p2TD}`, detail: `Sub attempts: ${(ss.p1_submissions as number) ?? 0} - ${(ss.p2_submissions as number) ?? 0}` },
      { label: 'Round State', value: periodLabel, detail: clockLabel },
    ];
  }

  // Racing (default fallback)
  const ss = tick.sport_state ?? {};
  const p1Lap = (ss.p1_lap as number) ?? 0;
  const totalLaps = (ss.total_laps as number) ?? 0;
  const gap = (ss.gap as number) ?? 0;
  const leader = (ss.leader as string) ?? 'p1';
  const p1Tire = (ss.p1_tire_wear as number) ?? 1;
  const p2Tire = (ss.p2_tire_wear as number) ?? 1;
  const p1Pits = (ss.p1_pit_stops as number) ?? 0;
  const p2Pits = (ss.p2_pit_stops as number) ?? 0;
  const p1DNF = (ss.p1_dnf as boolean) ?? false;
  const p2DNF = (ss.p2_dnf as boolean) ?? false;
  return [
    { label: 'Lap', value: `${p1Lap} / ${totalLaps}`, detail: `Gap: ${gap.toFixed(2)}s · Leader: ${leader === 'p1' ? 'Driver A' : 'Driver B'}` },
    { label: 'Tire Wear', value: `${Math.round(p1Tire * 100)}% / ${Math.round(p2Tire * 100)}%`, detail: `Pit stops: ${p1Pits} - ${p2Pits}` },
    { label: 'Status', value: p1DNF || p2DNF ? (p1DNF ? 'A DNF' : 'B DNF') : 'Running', detail: `Incidents: ${countEvents(events, ['yellow_flag', 'crash', 'dnf'])}` },
    { label: 'Race State', value: periodLabel, detail: clockLabel },
  ];
}

export function getTuningLensCopy(sport: SportType): string {
  const presentation = getSportPresentation(sport);
  return `Read these search results through a ${presentation.label.toLowerCase()} lens: optimize for ${presentation.rhythm}.`;
}

export function getAccentFillClass(sport: SportType): string {
  const fills: Record<SportType, string> = {
    soccer: 'bg-emerald-300',
    basketball: 'bg-amber-300',
    baseball: 'bg-lime-300',
    football: 'bg-red-300',
    hockey: 'bg-cyan-300',
    tennis: 'bg-blue-200',
    golf: 'bg-green-200',
    cricket: 'bg-yellow-200',
    boxing: 'bg-rose-200',
    mma: 'bg-slate-200',
    racing: 'bg-neutral-200',
  };

  return fills[sport];
}

export function getAccentFillColor(sport: SportType): string {
  const fills: Record<SportType, string> = {
    soccer: '#6ee7b7',
    basketball: '#fcd34d',
    baseball: '#bef264',
    football: '#fca5a5',
    hockey: '#67e8f9',
    tennis: '#bfdbfe',
    golf: '#bbf7d0',
    cricket: '#fde68a',
    boxing: '#fecdd3',
    mma: '#e2e8f0',
    racing: '#f5f5f5',
  };

  return fills[sport];
}

export function getTuningParamLabel(sport: SportType, key: string): string {
  const labels: Partial<Record<SportType, Record<string, string>>> = {
    soccer: {
      attack_factor: 'Final-Third Aggression',
      defense_factor: 'Defensive Shape',
      pressing: 'Press Intensity',
      pace: 'Transition Tempo',
    },
    basketball: {
      attack_factor: 'Shot Creation',
      defense_factor: 'Perimeter Resistance',
      pace: 'Possession Tempo',
      three_point_tendency: 'Three-Point Volume',
    },
    baseball: {
      attack_factor: 'Run Creation',
      defense_factor: 'Run Suppression',
      pace: 'At-Bat Tempo',
    },
    football: {
      attack_factor: 'Drive Efficiency',
      defense_factor: 'Down-to-Down Resistance',
      pace: 'Play Tempo',
      blitz_frequency: 'Pressure Rate',
    },
    hockey: {
      attack_factor: 'Chance Creation',
      defense_factor: 'Zone Denial',
      pace: 'Shift Tempo',
      forecheck_intensity: 'Forecheck Pressure',
    },
    tennis: {
      attack_factor: 'Point Finishing',
      defense_factor: 'Rally Resilience',
      serve_aggression: 'Serve Pressure',
      net_approach: 'Net Frequency',
    },
    golf: {
      attack_factor: 'Scoring Aggression',
      defense_factor: 'Mistake Avoidance',
      risk_taking: 'Course Risk',
    },
    cricket: {
      attack_factor: 'Run Pressure',
      defense_factor: 'Wicket Control',
      batting_aggression: 'Batting Intent',
      bowling_variation: 'Bowling Variation',
    },
    boxing: {
      attack_factor: 'Combination Volume',
      defense_factor: 'Defensive Guard',
      aggression_level: 'Forward Pressure',
      counter_tendency: 'Counter Timing',
    },
    mma: {
      attack_factor: 'Offensive Threat',
      defense_factor: 'Damage Avoidance',
      clinch_tendency: 'Clinch Control',
      counter_tendency: 'Counter Timing',
    },
    racing: {
      attack_factor: 'Attack Window',
      defense_factor: 'Race Stability',
      tire_management: 'Tire Preservation',
      pit_strategy: 'Pit Timing',
    },
  };

  return labels[sport]?.[key] ?? humanizeToken(key);
}

export function averagePlayerRating(players: Array<{ attributes?: Record<string, number> }>): number {
  const ratings = players
    .map((player) => attributeAverage(player.attributes ?? {}))
    .filter((value) => !Number.isNaN(value));

  if (ratings.length === 0) {
    return 0;
  }

  return Math.round(ratings.reduce((sum, value) => sum + value, 0) / ratings.length);
}

export function attributeAverage(attributes: Record<string, number>): number {
  const values = Object.values(attributes);
  if (values.length === 0) {
    return 0;
  }

  return Math.round((values.reduce((sum, value) => sum + value, 0) / values.length) * 100);
}

export function topAttribute(attributes: Record<string, number>): { key: string; label: string; value: number } | null {
  const entry = Object.entries(attributes).sort((left, right) => right[1] - left[1])[0];
  if (!entry) {
    return null;
  }

  return { key: entry[0], label: humanizeToken(entry[0]), value: Math.round(entry[1] * 100) };
}