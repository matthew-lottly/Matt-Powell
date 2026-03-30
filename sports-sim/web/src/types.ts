/* Shared TypeScript types for the frontend */

export type SportType = 'soccer' | 'basketball' | 'baseball';

export interface SimConfig {
  sport: SportType;
  seed?: number | null;
  fidelity: 'fast' | 'medium' | 'high';
  ticks_per_second: number;
  enable_fatigue: boolean;
  enable_injuries: boolean;
  enable_weather: boolean;
  enable_momentum: boolean;
  weather: string;
  temperature_c: number;
  wind_speed_kph: number;
}

export interface SimEvent {
  type: string;
  time: number;
  period: number;
  description: string;
}

export interface SimSummary {
  game_id: string;
  sport: string;
  home_team: string;
  away_team: string;
  home_score: number;
  away_score: number;
  is_finished: boolean;
  total_events: number;
}

export interface StreamTick {
  game_id: string;
  clock: number;
  period: number;
  home_score: number;
  away_score: number;
  home_momentum: number;
  away_momentum: number;
  is_finished: boolean;
  events: { type: string; time: number; description: string }[];
}

export const DEFAULT_CONFIG: SimConfig = {
  sport: 'soccer',
  seed: null,
  fidelity: 'medium',
  ticks_per_second: 10,
  enable_fatigue: true,
  enable_injuries: true,
  enable_weather: true,
  enable_momentum: true,
  weather: 'clear',
  temperature_c: 22,
  wind_speed_kph: 0,
};

export const SPORT_LABELS: Record<SportType, string> = {
  soccer: 'Soccer',
  basketball: 'Basketball',
  baseball: 'Baseball',
};

export const SPORT_COLORS: Record<SportType, string> = {
  soccer: '#2d8a4e',
  basketball: '#c6884a',
  baseball: '#5a8f3c',
};
