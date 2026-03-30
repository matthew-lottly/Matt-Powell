import { useEffect, useState } from 'react';
import type { SimConfig, SportCapabilities, SportType, TeamOption, TeamSliders } from '../types';
import * as api from '../api';
import { DEFAULT_SLIDERS } from '../types';

const WEATHERS = ['clear', 'cloudy', 'rain', 'snow', 'wind', 'extreme_heat', 'fog', 'freezing', 'humid'];
const FIDELITIES = ['fast', 'medium', 'high'] as const;

/** Slider labels relevant to each sport */
const SPORT_SLIDERS: Record<SportType, { key: keyof TeamSliders; label: string }[]> = {
  soccer: [
    { key: 'offensive_aggression', label: 'Offense' },
    { key: 'defensive_intensity', label: 'Defense' },
    { key: 'pace', label: 'Pace' },
    { key: 'pressing', label: 'Pressing' },
    { key: 'substitution_aggression', label: 'Sub Aggression' },
  ],
  basketball: [
    { key: 'offensive_aggression', label: 'Offense' },
    { key: 'defensive_intensity', label: 'Defense' },
    { key: 'pace', label: 'Pace' },
    { key: 'three_point_tendency', label: '3-PT Tendency' },
    { key: 'steal_attempt_rate', label: 'Steal Rate' },
  ],
  baseball: [
    { key: 'offensive_aggression', label: 'Offense' },
    { key: 'defensive_intensity', label: 'Defense' },
    { key: 'pace', label: 'Pace' },
    { key: 'bunt_tendency', label: 'Bunt Tendency' },
    { key: 'steal_attempt_rate', label: 'Steal Rate' },
  ],
  football: [
    { key: 'offensive_aggression', label: 'Offense' },
    { key: 'defensive_intensity', label: 'Defense' },
    { key: 'run_pass_ratio', label: 'Run/Pass Ratio' },
    { key: 'blitz_frequency', label: 'Blitz Frequency' },
    { key: 'substitution_aggression', label: 'Sub Aggression' },
  ],
  hockey: [
    { key: 'offensive_aggression', label: 'Offense' },
    { key: 'defensive_intensity', label: 'Defense' },
    { key: 'forecheck_intensity', label: 'Forecheck' },
    { key: 'power_play_aggression', label: 'Power Play' },
    { key: 'line_change_frequency', label: 'Line Changes' },
  ],
  tennis: [
    { key: 'serve_aggression', label: 'Serve Power' },
    { key: 'net_approach', label: 'Net Approach' },
    { key: 'offensive_aggression', label: 'Offense' },
    { key: 'defensive_intensity', label: 'Defense' },
    { key: 'pace', label: 'Pace' },
  ],
  golf: [
    { key: 'risk_taking', label: 'Risk Taking' },
    { key: 'offensive_aggression', label: 'Aggression' },
    { key: 'pace', label: 'Pace' },
  ],
  cricket: [
    { key: 'batting_aggression', label: 'Batting Aggression' },
    { key: 'bowling_variation', label: 'Bowling Variation' },
    { key: 'offensive_aggression', label: 'Offense' },
    { key: 'defensive_intensity', label: 'Defense' },
    { key: 'pace', label: 'Pace' },
  ],
  boxing: [
    { key: 'aggression_level', label: 'Aggression' },
    { key: 'counter_tendency', label: 'Counter Punching' },
    { key: 'clinch_tendency', label: 'Clinch Tendency' },
    { key: 'defensive_intensity', label: 'Defense' },
    { key: 'pace', label: 'Pace' },
  ],
  mma: [
    { key: 'aggression_level', label: 'Aggression' },
    { key: 'counter_tendency', label: 'Counter Tendency' },
    { key: 'clinch_tendency', label: 'Grappling' },
    { key: 'offensive_aggression', label: 'Striking' },
    { key: 'pace', label: 'Pace' },
  ],
  racing: [
    { key: 'overtake_aggression', label: 'Overtake Aggression' },
    { key: 'tire_management', label: 'Tire Management' },
    { key: 'pit_strategy', label: 'Pit Strategy' },
    { key: 'pace', label: 'Pace' },
    { key: 'risk_taking', label: 'Risk Taking' },
  ],
};

interface Props {
  config: SimConfig;
  onChange: (c: SimConfig) => void;
  disabled: boolean;
}

export default function ConfigPanel({ config, onChange, disabled }: Props) {
  const [teams, setTeams] = useState<TeamOption[]>([]);
  const [leagues, setLeagues] = useState<any[]>([]);
  const [venues, setVenues] = useState<any[]>([]);
  const [caps, setCaps] = useState<SportCapabilities | null>(null);
  const [showSliders, setShowSliders] = useState(false);

  const set = <K extends keyof SimConfig>(key: K, val: SimConfig[K]) =>
    onChange({ ...config, [key]: val });

  // Load sport capabilities when sport changes
  useEffect(() => {
    api.fetchSportCapabilities(config.sport).then(setCaps).catch(() => setCaps(null));
  }, [config.sport]);

  // Load available leagues and teams when sport or league changes
  useEffect(() => {
    // fetch leagues for sport
    api.fetchLeagues(config.sport).then((l: any[]) => setLeagues(l)).catch(() => setLeagues([]));

    // fetch teams (backend supports optional league query) and venues
    (async () => {
      try {
        const teams = await api.fetchTeams(config.sport, config.league ?? '');
        setTeams(teams);
        try {
          const v = await api.fetchVenues(config.sport, config.league ?? undefined);
          setVenues(v || []);
        } catch (e) {
          setVenues([]);
        }
      } catch (err) {
        setTeams([]);
        setVenues([]);
      }
    })();
  }, [config.sport, config.league]);

  // Auto-select home venue when home team changes and we have a matching venue
  useEffect(() => {
    if (!config.home_team) return;
    // If user already set a custom venue_name, don't override
    if (config.venue_name) return;
    const match = venues.find((v) => v.abbreviation === config.home_team);
    if (match) {
      set('venue_name', match.name);
      set('venue_type', match.venue_type);
      set('surface_type', match.surface);
    }
  }, [config.home_team, venues]);

  const sliderDefs = SPORT_SLIDERS[config.sport] ?? [];

  const updateHomeSlider = (key: keyof TeamSliders, val: number) => {
    const current = config.home_sliders ?? { ...DEFAULT_SLIDERS };
    onChange({ ...config, home_sliders: { ...current, [key]: val } });
  };
  const updateAwaySlider = (key: keyof TeamSliders, val: number) => {
    const current = config.away_sliders ?? { ...DEFAULT_SLIDERS };
    onChange({ ...config, away_sliders: { ...current, [key]: val } });
  };

  return (
    <div className="bg-gray-900 border border-gray-800 rounded-xl p-4 space-y-4 text-sm">
      <h3 className="font-semibold text-gray-200">Configuration</h3>

      {/* Sport */}
      <label className="block">
        <span className="text-gray-400 text-xs">Sport</span>
        <select
          value={config.sport}
          onChange={(e) => {
            const s = e.target.value as SportType;
            onChange({ ...config, sport: s, home_team: null, away_team: null });
          }}
          disabled={disabled}
          className="mt-1 block w-full bg-gray-800 border border-gray-700 rounded px-2 py-1.5 text-gray-200"
        >
          <option value="soccer">Soccer</option>
          <option value="basketball">Basketball</option>
          <option value="baseball">Baseball</option>
          <option value="football">Football</option>
          <option value="hockey">Hockey</option>
          <option value="tennis">Tennis</option>
          <option value="golf">Golf</option>
          <option value="cricket">Cricket</option>
          <option value="boxing">Boxing</option>
          <option value="mma">MMA</option>
          <option value="racing">Racing</option>
        </select>
      </label>

      {/* Team Selection */}
      {/* League Selection */}
      {leagues.length > 0 && (
        <label className="block">
          <span className="text-gray-400 text-xs">League</span>
          <select
            value={config.league ?? ''}
            onChange={(e) => set('league', e.target.value || null)}
            disabled={disabled}
            className="mt-1 block w-full bg-gray-800 border border-gray-700 rounded px-2 py-1.5 text-gray-200"
          >
            <option value="">Default / All</option>
            {leagues.map((l) => (
              <option key={l.id} value={l.id}>{l.name}</option>
            ))}
          </select>
        </label>
      )}

      {/* League metadata */}
      {config.league && (
        (() => {
          const meta = leagues.find((x) => x.id === config.league);
          if (!meta) return null;
          return (
            <div className="text-xs text-gray-400 mt-1">
              Rosters: {meta.roster_available ? 'available' : 'not available'} · Venues: {meta.venues ? 'yes' : 'no'} · Source: {meta.source}
            </div>
          );
        })()
      )}
      {teams.length > 0 && (
        <>
          <label className="block">
            <span className="text-gray-400 text-xs">Home Team</span>
            <select
              value={config.home_team ?? ''}
              onChange={(e) => set('home_team', e.target.value || null)}
              disabled={disabled}
              className="mt-1 block w-full bg-gray-800 border border-gray-700 rounded px-2 py-1.5 text-gray-200"
            >
              <option value="">Random / Default</option>
              {teams.map((t) => (
                <option key={t.abbreviation} value={t.abbreviation}>
                  {t.city} {t.name}
                </option>
              ))}
            </select>
          </label>
          <label className="block">
            <span className="text-gray-400 text-xs">Away Team</span>
            <select
              value={config.away_team ?? ''}
              onChange={(e) => set('away_team', e.target.value || null)}
              disabled={disabled}
              className="mt-1 block w-full bg-gray-800 border border-gray-700 rounded px-2 py-1.5 text-gray-200"
            >
              <option value="">Random / Default</option>
              {teams.map((t) => (
                <option key={t.abbreviation} value={t.abbreviation}>
                  {t.city} {t.name}
                </option>
              ))}
            </select>
          </label>
        </>
      )}

      {/* Venue Selection */}
      {venues.length > 0 ? (
        <label className="block">
          <span className="text-gray-400 text-xs">Venue</span>
          <select
            value={config.venue_name ?? ''}
            onChange={(e) => {
              const v = venues.find((x) => x.abbreviation === e.target.value);
              set('venue_name', v ? v.name : (e.target.value || null));
              set('venue_type', v ? v.venue_type : null);
              set('surface_type', v ? v.surface : null);
            }}
            disabled={disabled}
            className="mt-1 block w-full bg-gray-800 border border-gray-700 rounded px-2 py-1.5 text-gray-200"
          >
            <option value="">Default / Random</option>
            {venues.map((vn) => (
              <option key={vn.abbreviation} value={vn.abbreviation}>{vn.name} — {vn.city}</option>
            ))}
          </select>
        </label>
      ) : (
        <label className="block">
          <span className="text-gray-400 text-xs">Venue</span>
          <input
            type="text"
            value={config.venue_name ?? ''}
            onChange={(e) => set('venue_name', e.target.value || null)}
            disabled={disabled}
            placeholder="Custom venue name"
            className="mt-1 block w-full bg-gray-800 border border-gray-700 rounded px-2 py-1.5 text-gray-200"
          />
        </label>
      )}

      {/* Fidelity */}
      <label className="block">
        <span className="text-gray-400 text-xs">Fidelity</span>
        <select
          value={config.fidelity}
          onChange={(e) => set('fidelity', e.target.value as (typeof FIDELITIES)[number])}
          disabled={disabled}
          className="mt-1 block w-full bg-gray-800 border border-gray-700 rounded px-2 py-1.5 text-gray-200"
        >
          {FIDELITIES.map((f) => (
            <option key={f} value={f}>{f}</option>
          ))}
        </select>
      </label>

      {/* Seed */}
      <label className="block">
        <span className="text-gray-400 text-xs">Seed (optional)</span>
        <input
          type="number"
          value={config.seed ?? ''}
          onChange={(e) => set('seed', e.target.value ? Number(e.target.value) : null)}
          disabled={disabled}
          placeholder="random"
          className="mt-1 block w-full bg-gray-800 border border-gray-700 rounded px-2 py-1.5 text-gray-200"
        />
      </label>

      {/* Weather — only show for weather-affected sports */}
      {(!caps || caps.weather_affected) && (
        <label className="block">
          <span className="text-gray-400 text-xs">Weather</span>
          <select
            value={config.weather}
            onChange={(e) => set('weather', e.target.value)}
            disabled={disabled}
            className="mt-1 block w-full bg-gray-800 border border-gray-700 rounded px-2 py-1.5 text-gray-200"
          >
            {WEATHERS.map((w) => (
              <option key={w} value={w}>{w.replace(/_/g, ' ')}</option>
            ))}
          </select>
        </label>
      )}

      {/* Temp + Wind + Humidity — conditional per capability */}
      {(!caps || caps.temperature_affected || caps.wind_affected || caps.humidity_affected) && (
        <div className="grid grid-cols-3 gap-2">
          {(!caps || caps.temperature_affected) && (
            <label className="block">
              <span className="text-gray-400 text-xs">Temp °C</span>
              <input
                type="number"
                value={config.temperature_c}
                onChange={(e) => set('temperature_c', Number(e.target.value))}
                disabled={disabled}
                className="mt-1 block w-full bg-gray-800 border border-gray-700 rounded px-2 py-1.5 text-gray-200"
              />
            </label>
          )}
          {(!caps || caps.wind_affected) && (
            <label className="block">
              <span className="text-gray-400 text-xs">Wind kph</span>
              <input
                type="number"
                value={config.wind_speed_kph}
                onChange={(e) => set('wind_speed_kph', Number(e.target.value))}
                disabled={disabled}
                className="mt-1 block w-full bg-gray-800 border border-gray-700 rounded px-2 py-1.5 text-gray-200"
              />
            </label>
          )}
          {(!caps || caps.humidity_affected) && (
            <label className="block">
              <span className="text-gray-400 text-xs">Humidity</span>
              <input
                type="number"
                step="0.1"
                min="0"
                max="1"
                value={config.humidity}
                onChange={(e) => set('humidity', Number(e.target.value))}
                disabled={disabled}
                className="mt-1 block w-full bg-gray-800 border border-gray-700 rounded px-2 py-1.5 text-gray-200"
              />
            </label>
          )}
        </div>
      )}

      {/* Indoor sport indicator */}
      {caps && !caps.is_outdoor && (
        <div className="text-xs text-gray-500 italic">
          Indoor sport — weather conditions do not apply
        </div>
      )}

      {/* Toggles */}
      <div className="space-y-2">
        {[
          ['enable_fatigue', 'Fatigue'],
          ['enable_injuries', 'Injuries'],
          ['enable_weather', 'Weather FX'],
          ['enable_momentum', 'Momentum'],
          ['enable_venue_effects', 'Venue FX'],
          ['enable_coach_effects', 'Coach FX'],
          ['enable_surface_effects', 'Surface FX'],
        ].map(([key, label]) => (
          <label key={key} className="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              checked={config[key as keyof SimConfig] as boolean}
              onChange={(e) => set(key as keyof SimConfig, e.target.checked as never)}
              disabled={disabled}
              className="rounded bg-gray-800 border-gray-700 text-blue-600 focus:ring-blue-500"
            />
            <span className="text-gray-300 text-xs">{label}</span>
          </label>
        ))}
      </div>

      {/* Team Sliders */}
      <button
        type="button"
        onClick={() => setShowSliders(!showSliders)}
        className="w-full text-left text-xs text-blue-400 hover:text-blue-300 pt-1"
      >
        {showSliders ? '▾ Hide Sliders' : '▸ Team Strategy Sliders'}
      </button>

      {showSliders && (
        <div className="space-y-3 border-t border-gray-800 pt-3">
          {/* Home sliders */}
          <div>
            <p className="text-xs font-medium text-blue-300 mb-1">Home Team</p>
            {sliderDefs.map(({ key, label }) => (
              <label key={`home-${key}`} className="flex items-center gap-2 text-xs">
                <span className="text-gray-400 w-24 shrink-0">{label}</span>
                <input
                  type="range"
                  min="0"
                  max="1"
                  step="0.05"
                  value={(config.home_sliders ?? DEFAULT_SLIDERS)[key]}
                  onChange={(e) => updateHomeSlider(key, Number(e.target.value))}
                  disabled={disabled}
                  className="flex-1"
                />
                <span className="text-gray-500 w-8 text-right">
                  {((config.home_sliders ?? DEFAULT_SLIDERS)[key] * 100).toFixed(0)}%
                </span>
              </label>
            ))}
          </div>
          {/* Away sliders */}
          <div>
            <p className="text-xs font-medium text-red-300 mb-1">Away Team</p>
            {sliderDefs.map(({ key, label }) => (
              <label key={`away-${key}`} className="flex items-center gap-2 text-xs">
                <span className="text-gray-400 w-24 shrink-0">{label}</span>
                <input
                  type="range"
                  min="0"
                  max="1"
                  step="0.05"
                  value={(config.away_sliders ?? DEFAULT_SLIDERS)[key]}
                  onChange={(e) => updateAwaySlider(key, Number(e.target.value))}
                  disabled={disabled}
                  className="flex-1"
                />
                <span className="text-gray-500 w-8 text-right">
                  {((config.away_sliders ?? DEFAULT_SLIDERS)[key] * 100).toFixed(0)}%
                </span>
              </label>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
