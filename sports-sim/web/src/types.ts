/* Shared TypeScript types for the frontend */

export type SportType = 'soccer' | 'basketball' | 'baseball' | 'football' | 'hockey' | 'tennis' | 'golf' | 'cricket' | 'boxing' | 'mma' | 'racing';

export interface TeamSliders {
  offensive_aggression: number;
  defensive_intensity: number;
  pace: number;
  pressing: number;
  three_point_tendency: number;
  run_pass_ratio: number;
  steal_attempt_rate: number;
  bunt_tendency: number;
  blitz_frequency: number;
  substitution_aggression: number;
  // Hockey
  forecheck_intensity: number;
  power_play_aggression: number;
  line_change_frequency: number;
  // Tennis
  serve_aggression: number;
  net_approach: number;
  // Golf
  risk_taking: number;
  // Cricket
  batting_aggression: number;
  bowling_variation: number;
  // Boxing/MMA
  aggression_level: number;
  counter_tendency: number;
  clinch_tendency: number;
  // Racing
  tire_management: number;
  pit_strategy: number;
  overtake_aggression: number;
}

export interface SimConfig {
  sport: SportType;
  league?: string | null;
  seed?: number | null;
  fidelity: 'fast' | 'medium' | 'high';
  ticks_per_second: number;
  enable_fatigue: boolean;
  enable_injuries: boolean;
  enable_weather: boolean;
  enable_momentum: boolean;
  enable_venue_effects: boolean;
  enable_coach_effects: boolean;
  enable_surface_effects: boolean;
  weather: string;
  temperature_c: number;
  wind_speed_kph: number;
  humidity: number;
  // Team selection
  home_team?: string | null;
  away_team?: string | null;
  // Venue override
  venue_name?: string | null;
  venue_type?: string | null;
  surface_type?: string | null;
  altitude_m?: number | null;
  // Sliders
  home_sliders?: TeamSliders | null;
  away_sliders?: TeamSliders | null;
}

export interface TeamOption {
  abbreviation: string;
  name: string;
  city: string;
}

export interface VenueOption {
  abbreviation: string;
  name: string;
  city: string;
  venue_type: string;
  surface: string;
  capacity: number;
  altitude_m: number;
  weather_exposed: boolean;
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
  home_team: string;
  away_team: string;
  home_score: number;
  away_score: number;
  home_momentum: number;
  away_momentum: number;
  is_finished: boolean;
  events: { type: string; time: number; description: string }[];
}

export const DEFAULT_SLIDERS: TeamSliders = {
  offensive_aggression: 0.5,
  defensive_intensity: 0.5,
  pace: 0.5,
  pressing: 0.5,
  three_point_tendency: 0.5,
  run_pass_ratio: 0.5,
  steal_attempt_rate: 0.3,
  bunt_tendency: 0.2,
  blitz_frequency: 0.3,
  substitution_aggression: 0.5,
  forecheck_intensity: 0.5,
  power_play_aggression: 0.5,
  line_change_frequency: 0.5,
  serve_aggression: 0.5,
  net_approach: 0.3,
  risk_taking: 0.5,
  batting_aggression: 0.5,
  bowling_variation: 0.5,
  aggression_level: 0.5,
  counter_tendency: 0.5,
  clinch_tendency: 0.3,
  tire_management: 0.5,
  pit_strategy: 0.5,
  overtake_aggression: 0.5,
};

export const DEFAULT_CONFIG: SimConfig = {
  sport: 'soccer',
  seed: null,
  fidelity: 'medium',
  ticks_per_second: 10,
  enable_fatigue: true,
  enable_injuries: true,
  enable_weather: true,
  enable_momentum: true,
  enable_venue_effects: true,
  enable_coach_effects: true,
  enable_surface_effects: true,
  weather: 'clear',
  temperature_c: 22,
  wind_speed_kph: 0,
  humidity: 0.5,
  home_team: null,
  away_team: null,
};

export const SPORT_LABELS: Record<SportType, string> = {
  soccer: 'Soccer',
  basketball: 'Basketball',
  baseball: 'Baseball',
  football: 'Football',
  hockey: 'Hockey',
  tennis: 'Tennis',
  golf: 'Golf',
  cricket: 'Cricket',
  boxing: 'Boxing',
  mma: 'MMA',
  racing: 'Racing',
};

export const SPORT_COLORS: Record<SportType, string> = {
  soccer: '#2d8a4e',
  basketball: '#c6884a',
  baseball: '#5a8f3c',
  football: '#3b5998',
  hockey: '#1e90ff',
  tennis: '#c4d600',
  golf: '#228b22',
  cricket: '#8b4513',
  boxing: '#dc143c',
  mma: '#8b0000',
  racing: '#ff4500',
};
