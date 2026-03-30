import { useCallback, useRef, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import ConfigPanel from '../components/ConfigPanel.tsx';
import Scoreboard from '../components/Scoreboard.tsx';
import FieldView from '../components/FieldView.tsx';
import EventLog from '../components/EventLog.tsx';
import MomentumBar from '../components/MomentumBar.tsx';
import { streamSimulation } from '../api';
import { DEFAULT_CONFIG, type SimConfig, type SportType, type StreamTick } from '../types';

export default function SimulationPage() {
  const [params] = useSearchParams();
  const sportParam = (params.get('sport') ?? 'soccer') as SportType;

  const [config, setConfig] = useState<SimConfig>({ ...DEFAULT_CONFIG, sport: sportParam });
  const [running, setRunning] = useState(false);
  const [finished, setFinished] = useState(false);
  const [ticks, setTicks] = useState<StreamTick[]>([]);
  const wsRef = useRef<WebSocket | null>(null);

  const latestTick = ticks[ticks.length - 1] ?? null;

  const handleStart = useCallback(() => {
    setTicks([]);
    setRunning(true);
    setFinished(false);

    wsRef.current = streamSimulation(
      config,
      (tick) => setTicks((prev) => [...prev, tick]),
      () => {
        setRunning(false);
        setFinished(true);
      },
      (err) => {
        console.error('WS error', err);
        setRunning(false);
      },
    );
  }, [config]);

  const handleStop = useCallback(() => {
    wsRef.current?.close();
    setRunning(false);
  }, []);

  // Flatten all events from all ticks
  const allEvents = ticks.flatMap((t) =>
    t.events.map((e) => ({ ...e, period: t.period })),
  );

  return (
    <div className="max-w-7xl mx-auto space-y-6">
      <h2 className="text-2xl font-bold">Simulation</h2>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* ── left: config ── */}
        <div className="lg:col-span-3 space-y-4">
          <ConfigPanel config={config} onChange={setConfig} disabled={running} />
          <div className="flex gap-2">
            {!running ? (
              <button
                onClick={handleStart}
                className="flex-1 bg-blue-600 hover:bg-blue-500 text-white font-medium py-2 rounded-lg transition"
              >
                {finished ? 'Run Again' : 'Start'}
              </button>
            ) : (
              <button
                onClick={handleStop}
                className="flex-1 bg-red-600 hover:bg-red-500 text-white font-medium py-2 rounded-lg transition"
              >
                Stop
              </button>
            )}
          </div>
        </div>

        {/* ── center: field + scoreboard ── */}
        <div className="lg:col-span-6 space-y-4">
          <Scoreboard tick={latestTick} sport={config.sport} />
          <MomentumBar tick={latestTick} />
          <FieldView sport={config.sport} tick={latestTick} />
        </div>

        {/* ── right: event log ── */}
        <div className="lg:col-span-3">
          <EventLog events={allEvents} sport={config.sport} />
        </div>
      </div>
    </div>
  );
}
