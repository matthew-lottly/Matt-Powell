import type { SimConfig, SportType } from '../types';

const WEATHERS = ['clear', 'cloudy', 'rain', 'snow', 'wind', 'extreme_heat'];
const FIDELITIES = ['fast', 'medium', 'high'] as const;

interface Props {
  config: SimConfig;
  onChange: (c: SimConfig) => void;
  disabled: boolean;
}

export default function ConfigPanel({ config, onChange, disabled }: Props) {
  const set = <K extends keyof SimConfig>(key: K, val: SimConfig[K]) =>
    onChange({ ...config, [key]: val });

  return (
    <div className="bg-gray-900 border border-gray-800 rounded-xl p-4 space-y-4 text-sm">
      <h3 className="font-semibold text-gray-200">Configuration</h3>

      {/* Sport */}
      <label className="block">
        <span className="text-gray-400 text-xs">Sport</span>
        <select
          value={config.sport}
          onChange={(e) => set('sport', e.target.value as SportType)}
          disabled={disabled}
          className="mt-1 block w-full bg-gray-800 border border-gray-700 rounded px-2 py-1.5 text-gray-200"
        >
          <option value="soccer">Soccer</option>
          <option value="basketball">Basketball</option>
          <option value="baseball">Baseball</option>
        </select>
      </label>

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

      {/* Weather */}
      <label className="block">
        <span className="text-gray-400 text-xs">Weather</span>
        <select
          value={config.weather}
          onChange={(e) => set('weather', e.target.value)}
          disabled={disabled}
          className="mt-1 block w-full bg-gray-800 border border-gray-700 rounded px-2 py-1.5 text-gray-200"
        >
          {WEATHERS.map((w) => (
            <option key={w} value={w}>{w.replace('_', ' ')}</option>
          ))}
        </select>
      </label>

      {/* Temp + Wind */}
      <div className="grid grid-cols-2 gap-2">
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
      </div>

      {/* Toggles */}
      <div className="space-y-2">
        {[
          ['enable_fatigue', 'Fatigue'],
          ['enable_injuries', 'Injuries'],
          ['enable_weather', 'Weather FX'],
          ['enable_momentum', 'Momentum'],
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
    </div>
  );
}
