import { useCallback, useEffect, useRef, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import ConfigPanel from '../components/ConfigPanel.tsx';
import Scoreboard from '../components/Scoreboard.tsx';
import FieldView from '../components/FieldView.tsx';
import EventLog from '../components/EventLog.tsx';
import MomentumBar from '../components/MomentumBar.tsx';
import SportInsightCards from '../components/SportInsightCards.tsx';
import PostGameSummary from '../components/PostGameSummary.tsx';
import ScoreChart from '../components/ScoreChart.tsx';
import PlaybackControls from '../components/PlaybackControls.tsx';
import PlayerCardModal from '../components/PlayerCardModal.tsx';
import { streamSimulation, exportJsonUrl, exportCsvUrl } from '../api';
import { DEFAULT_CONFIG, type PlayerCardData, type SimConfig, type SportType, type StreamTick } from '../types';
import { getSportPresentation } from '../sportPresentation';

const STORAGE_KEY = 'sports-sim-config';

function loadSavedConfig(sportParam: SportType, leagueParam: string | null, homeParam: string | null, awayParam: string | null): SimConfig {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (raw) {
      const saved = JSON.parse(raw) as SimConfig;
      // Override sport if query param provided
      return {
        ...DEFAULT_CONFIG,
        ...saved,
        sport: sportParam,
        league: leagueParam ?? saved.league ?? null,
        home_team: homeParam ?? saved.home_team ?? null,
        away_team: awayParam ?? saved.away_team ?? null,
      };
    }
  } catch { /* ignore corrupt storage */ }
  return {
    ...DEFAULT_CONFIG,
    sport: sportParam,
    league: leagueParam,
    home_team: homeParam,
    away_team: awayParam,
  };
}

export default function SimulationPage() {
  const [params] = useSearchParams();
  const sportParam = (params.get('sport') ?? 'soccer') as SportType;
  const leagueParam = params.get('league');
  const homeParam = params.get('home');
  const awayParam = params.get('away');

  const [config, setConfig] = useState<SimConfig>(() => loadSavedConfig(sportParam, leagueParam, homeParam, awayParam));
  const [running, setRunning] = useState(false);
  const [finished, setFinished] = useState(false);
  const [connecting, setConnecting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [ticks, setTicks] = useState<StreamTick[]>([]);
  const [playbackIndex, setPlaybackIndex] = useState<number>(-1);
  const [isPaused, setIsPaused] = useState(false);
  const [playbackSpeed, setPlaybackSpeed] = useState(1);
  const [showHeatmap, setShowHeatmap] = useState(false);
  const [heatmapTeam, setHeatmapTeam] = useState<'home' | 'away' | null>(null);
  const [selectedPlayer, setSelectedPlayer] = useState<PlayerCardData | null>(null);
  const [showRoster, setShowRoster] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const playbackTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Cleanup timer and WS on unmount
  useEffect(() => {
    return () => {
      if (playbackTimer.current) clearTimeout(playbackTimer.current);
      wsRef.current?.close();
    };
  }, []);

  useEffect(() => {
    setConfig((prev) => ({
      ...prev,
      sport: sportParam,
      league: leagueParam ?? prev.league ?? null,
      home_team: homeParam ?? prev.home_team ?? null,
      away_team: awayParam ?? prev.away_team ?? null,
    }));
  }, [sportParam, leagueParam, homeParam, awayParam]);

  // Persist config to localStorage on change
  useEffect(() => {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(config));
    } catch { /* quota exceeded — ignore */ }
  }, [config]);

  const isLive = running && !isPaused && playbackIndex < 0;
  const activeIndex = playbackIndex >= 0 ? Math.min(playbackIndex, ticks.length - 1) : ticks.length - 1;
  const latestTick = ticks[activeIndex] ?? null;
  const presentation = getSportPresentation(config.sport);
  const latestEvent = latestTick?.events[latestTick.events.length - 1] ?? null;

  // Replay timer for scrubbing through completed or paused simulations.
  useEffect(() => {
    if (isPaused || playbackIndex < 0) {
      if (playbackTimer.current) {
        clearTimeout(playbackTimer.current);
        playbackTimer.current = null;
      }
      return;
    }

    if (playbackIndex >= ticks.length - 1) {
      if (running) {
        setPlaybackIndex(-1);
      } else {
        setIsPaused(true);
      }
      return;
    }

    const delayMs = Math.max(50, Math.round(1000 / Math.max(1, config.ticks_per_second * playbackSpeed)));
    playbackTimer.current = setTimeout(() => {
      setPlaybackIndex((prev) => (prev < 0 ? prev : Math.min(prev + 1, ticks.length - 1)));
    }, delayMs);

    return () => {
      if (playbackTimer.current) {
        clearTimeout(playbackTimer.current);
        playbackTimer.current = null;
      }
    };
  }, [config.ticks_per_second, isPaused, playbackIndex, playbackSpeed, running, ticks.length]);

  const handlePlaybackSeek = useCallback((idx: number) => {
    setPlaybackIndex(idx);
    if (running) setIsPaused(true);
  }, [running]);

  const handleTogglePause = useCallback(() => {
    if (ticks.length === 0) {
      return;
    }

    if (!isPaused) {
      if (running && playbackIndex < 0) {
        setPlaybackIndex(Math.max(ticks.length - 1, 0));
      }
      setIsPaused(true);
      return;
    }

    if (running && playbackIndex >= ticks.length - 1) {
      setPlaybackIndex(-1);
    } else if (!running && playbackIndex < 0) {
      setPlaybackIndex(0);
    }
    setIsPaused(false);
  }, [isPaused, playbackIndex, running, ticks.length]);

  const handleStepForward = useCallback(() => {
    if (ticks.length === 0) return;
    if (running) setIsPaused(true);
    setPlaybackIndex((prev) => Math.min((prev < 0 ? ticks.length - 1 : prev) + 1, ticks.length - 1));
  }, [running, ticks.length]);

  const handleStepBackward = useCallback(() => {
    if (ticks.length === 0) return;
    if (running) setIsPaused(true);
    setPlaybackIndex((prev) => Math.max((prev < 0 ? ticks.length - 1 : prev) - 1, 0));
  }, [running, ticks.length]);

  const handleGoToStart = useCallback(() => {
    if (ticks.length === 0) return;
    if (running) setIsPaused(true);
    setPlaybackIndex(0);
  }, [running, ticks.length]);

  const handleGoToEnd = useCallback(() => {
    if (ticks.length === 0) return;
    setPlaybackIndex(-1);
    if (!running) setPlaybackIndex(ticks.length - 1);
  }, [running, ticks.length]);

  const handleStart = useCallback(() => {
    setTicks([]);
    setRunning(true);
    setFinished(false);
    setConnecting(true);
    setError(null);
    setPlaybackIndex(-1);
    setIsPaused(false);
    setPlaybackSpeed(1);
    setShowHeatmap(false);
    setHeatmapTeam(null);

    wsRef.current = streamSimulation(
      config,
      (tick) => {
        setConnecting(false);
        setTicks((prev) => [...prev, tick]);
      },
      () => {
        setRunning(false);
        setFinished(true);
        setConnecting(false);
      },
      (err) => {
        console.error('WS error', err);
        setRunning(false);
        setConnecting(false);
        setError(err instanceof Error ? err.message : 'Connection failed');
      },
    );
  }, [config]);

  const handleStop = useCallback(() => {
    wsRef.current?.close();
    setRunning(false);
  }, []);

  // Flatten events up to the current playback position
  const visibleTicks = ticks.slice(0, activeIndex + 1);
  const allEvents = visibleTicks.flatMap((t) =>
    t.events.map((e) => ({ ...e, period: t.period })),
  );

  return (
    <div className="max-w-7xl mx-auto space-y-4 px-2 sm:px-4 lg:px-6">
      <section className={`rounded-[28px] border border-white/8 bg-gradient-to-br ${presentation.heroGradient} p-5 sm:p-6 shadow-[0_20px_60px_rgba(0,0,0,0.3)]`}>
        <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
          <div className="space-y-3">
            <div className={`inline-flex items-center gap-2 rounded-full border px-3 py-1 text-[11px] font-medium uppercase tracking-[0.2em] ${presentation.accentBadge}`}>
              {presentation.statusVerb}
            </div>
            <div>
              <h2 className="text-2xl sm:text-3xl font-bold">{presentation.label} Simulation</h2>
              <p className="mt-2 max-w-3xl text-sm text-slate-300">{presentation.headline}</p>
            </div>
            <div className="flex flex-wrap gap-2 text-xs text-slate-200">
              <span className="rounded-full border border-white/10 bg-white/5 px-3 py-1">{presentation.format}</span>
              <span className="rounded-full border border-white/10 bg-white/5 px-3 py-1">{presentation.rhythm}</span>
              {config.league && <span className="rounded-full border border-white/10 bg-white/5 px-3 py-1">League: {config.league.toUpperCase()}</span>}
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3 text-xs sm:min-w-[280px]">
            <div className="rounded-2xl border border-white/10 bg-black/15 p-3">
              <div className="text-slate-500 uppercase tracking-[0.16em]">Atmosphere</div>
              <div className="mt-1 text-slate-100">{presentation.atmosphere}</div>
            </div>
            <div className="rounded-2xl border border-white/10 bg-black/15 p-3">
              <div className="text-slate-500 uppercase tracking-[0.16em]">Latest event</div>
              <div className="mt-1 text-slate-100">{latestEvent?.description ?? presentation.emptyState}</div>
            </div>
          </div>
        </div>
      </section>

      {/* Mobile: Start/Stop button on top for easy access */}
      <div className="flex gap-2 lg:hidden">
        {!running ? (
          <button
            onClick={handleStart}
            className="flex-1 bg-blue-600 hover:bg-blue-500 text-white font-medium py-2.5 rounded-lg transition text-sm"
          >
            {finished ? 'Run Again' : 'Start'}
          </button>
        ) : (
          <button
            onClick={handleStop}
            className="flex-1 bg-red-600 hover:bg-red-500 text-white font-medium py-2.5 rounded-lg transition text-sm"
          >
            Stop
          </button>
        )}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4 lg:gap-6">
        {/* ── left: config ── */}
        <div className="lg:col-span-3 space-y-4 order-2 lg:order-1">
          <ConfigPanel config={config} onChange={setConfig} disabled={running} />
          <div className="hidden lg:flex gap-2">
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
        <div className="lg:col-span-6 space-y-3 sm:space-y-4 order-1 lg:order-2">
          {/* Connecting state */}
          {connecting && (
            <div className="rounded-2xl border border-white/8 bg-slate-900/85 p-6 text-center backdrop-blur-sm animate-pulse">
              <div className={`text-sm ${presentation.accentText}`}>Connecting to simulation...</div>
              <div className="mt-2 text-xs text-slate-500">Setting up {presentation.label.toLowerCase()} match</div>
            </div>
          )}
          {/* Error state */}
          {error && (
            <div className="rounded-2xl border border-red-500/30 bg-red-950/50 p-4 text-center">
              <div className="text-sm text-red-400">Simulation Error</div>
              <div className="mt-1 text-xs text-red-300/70">{error}</div>
              <button
                onClick={() => { setError(null); handleStart(); }}
                className="mt-2 px-4 py-1 text-xs rounded-lg bg-red-600 hover:bg-red-500 text-white transition"
              >
                Retry
              </button>
            </div>
          )}
          <Scoreboard tick={latestTick} sport={config.sport} />
          <SportInsightCards sport={config.sport} tick={latestTick} events={allEvents} />
          <MomentumBar tick={latestTick} sport={config.sport} />
          {ticks.length > 0 && (
            <div className="flex flex-wrap items-center gap-2 text-xs">
              <button
                onClick={() => {
                  setShowHeatmap(false);
                  setHeatmapTeam(null);
                }}
                className={`rounded-full border px-3 py-1 transition ${!showHeatmap ? 'border-white/20 bg-white/10 text-white' : 'border-white/10 bg-transparent text-slate-400 hover:bg-white/5'}`}
              >
                Overlay Off
              </button>
              <button
                onClick={() => {
                  setShowHeatmap(true);
                  setHeatmapTeam(null);
                }}
                className={`rounded-full border px-3 py-1 transition ${showHeatmap && heatmapTeam === null ? 'border-white/20 bg-white/10 text-white' : 'border-white/10 bg-transparent text-slate-400 hover:bg-white/5'}`}
              >
                Heatmap All
              </button>
              <button
                onClick={() => {
                  setShowHeatmap(true);
                  setHeatmapTeam('home');
                }}
                className={`rounded-full border px-3 py-1 transition ${showHeatmap && heatmapTeam === 'home' ? 'border-blue-400/30 bg-blue-500/10 text-blue-200' : 'border-white/10 bg-transparent text-slate-400 hover:bg-white/5'}`}
              >
                {latestTick?.home_team ?? 'Home'} Heatmap
              </button>
              <button
                onClick={() => {
                  setShowHeatmap(true);
                  setHeatmapTeam('away');
                }}
                className={`rounded-full border px-3 py-1 transition ${showHeatmap && heatmapTeam === 'away' ? 'border-red-400/30 bg-red-500/10 text-red-200' : 'border-white/10 bg-transparent text-slate-400 hover:bg-white/5'}`}
              >
                {latestTick?.away_team ?? 'Away'} Heatmap
              </button>
            </div>
          )}
          <FieldView sport={config.sport} tick={latestTick} showHeatmap={showHeatmap} heatmapTeam={heatmapTeam} />
          {ticks.length > 1 && <ScoreChart sport={config.sport} ticks={visibleTicks} />}
          {ticks.length > 0 && (
            <PlaybackControls
              totalTicks={ticks.length}
              currentIndex={activeIndex}
              isLive={isLive}
              isPaused={isPaused || finished}
              speed={playbackSpeed}
              onSeek={handlePlaybackSeek}
              onTogglePause={handleTogglePause}
              onSpeedChange={setPlaybackSpeed}
              onStepForward={handleStepForward}
              onStepBackward={handleStepBackward}
              onGoToStart={handleGoToStart}
              onGoToEnd={handleGoToEnd}
            />
          )}
          {finished && <PostGameSummary sport={config.sport} ticks={ticks} />}
          {finished && latestTick && (
            <div className="flex gap-2 text-xs">
              <a
                href={exportJsonUrl(latestTick.game_id)}
                download
                className="flex-1 text-center py-2 rounded-lg border border-white/10 bg-white/5 hover:bg-white/10 text-slate-300 transition"
              >
                Export JSON
              </a>
              <a
                href={exportCsvUrl(latestTick.game_id)}
                download
                className="flex-1 text-center py-2 rounded-lg border border-white/10 bg-white/5 hover:bg-white/10 text-slate-300 transition"
              >
                Export CSV
              </a>
            </div>
          )}
        </div>

        {/* ── right: event log + roster ── */}
        <div className="lg:col-span-3 order-3 space-y-3">
          {latestTick && latestTick.sport_state && (
            <div className="flex gap-1 text-xs">
              <button
                onClick={() => setShowRoster(false)}
                className={`flex-1 py-1.5 rounded-lg transition ${!showRoster ? 'bg-white/10 text-white' : 'bg-transparent text-slate-400 hover:bg-white/5'}`}
              >
                Events
              </button>
              <button
                onClick={() => setShowRoster(true)}
                className={`flex-1 py-1.5 rounded-lg transition ${showRoster ? 'bg-white/10 text-white' : 'bg-transparent text-slate-400 hover:bg-white/5'}`}
              >
                Roster
              </button>
            </div>
          )}
          {showRoster && latestTick?.sport_state ? (
            <div className="rounded-2xl border border-white/8 bg-slate-900/85 p-3 backdrop-blur-sm max-h-[60vh] overflow-y-auto space-y-3">
              {Object.entries(latestTick.sport_state).map(([key, val]) => (
                <div key={key} className="text-xs">
                  <span className="text-slate-500">{key}: </span>
                  <span className="text-slate-200">{typeof val === 'object' ? JSON.stringify(val) : String(val)}</span>
                </div>
              ))}
            </div>
          ) : (
            <EventLog events={allEvents} sport={config.sport} />
          )}
        </div>
      </div>

      <PlayerCardModal player={selectedPlayer} onClose={() => setSelectedPlayer(null)} />
    </div>
  );
}
