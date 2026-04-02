/* API client — REST helpers and WebSocket streaming */

import type { LeagueOption, SimConfig, SimSummary, SportCapabilities, StreamTick, TeamOption, VenueOption } from './types';

const BASE = '';  // proxied by Vite in dev

async function fetchWithRetry(url: string, init?: RequestInit, retries = 2): Promise<Response> {
  for (let i = 0; i <= retries; i++) {
    try {
      const res = await fetch(url, init);
      if (res.ok || res.status < 500) return res;
    } catch (err) {
      if (i === retries) throw err;
    }
    await new Promise((r) => setTimeout(r, Math.min(1000 * 2 ** i, 4000)));
  }
  return fetch(url, init); // final attempt
}

export async function fetchSports(): Promise<string[]> {
  const res = await fetchWithRetry(`${BASE}/api/sports`);
  const data = await res.json();
  return data.sports;
}

export async function fetchSportCapabilities(sport: string): Promise<SportCapabilities | null> {
  const res = await fetchWithRetry(`${BASE}/api/sports/${encodeURIComponent(sport)}/capabilities`);
  if (!res.ok) return null;
  return res.json();
}

export async function fetchTeams(sport: string, league?: string, page?: number, per_page?: number): Promise<TeamOption[]> {
  const params = new URLSearchParams();
  if (league) params.set('league', league);
  if (page) params.set('page', String(page));
  if (per_page) params.set('per_page', String(per_page));
  const q = params.toString() ? `?${params.toString()}` : '';
  const res = await fetchWithRetry(`${BASE}/api/teams/${encodeURIComponent(sport)}${q}`);
  if (!res.ok) return [];
  const data = await res.json();
  return data.teams;
}

export async function fetchLeagues(sport: string): Promise<LeagueOption[]> {
  const res = await fetchWithRetry(`${BASE}/api/leagues?sport=${encodeURIComponent(sport)}`);
  if (!res.ok) return [];
  const data = await res.json();
  return data.leagues ?? [];
}

export async function fetchLeagueRules(sport: string, leagueId: string): Promise<Record<string, unknown> | null> {
  const res = await fetchWithRetry(`${BASE}/api/leagues/${encodeURIComponent(sport)}/${encodeURIComponent(leagueId)}/rules`);
  if (!res.ok) return null;
  const data = await res.json();
  return data.rules ?? null;
}

export async function fetchVenues(sport: string, league?: string, page?: number, per_page?: number): Promise<VenueOption[]> {
  const params = new URLSearchParams();
  if (league) params.set('league', league);
  if (page) params.set('page', String(page));
  if (per_page) params.set('per_page', String(per_page));
  const q = params.toString() ? `?${params.toString()}` : '';
  const res = await fetchWithRetry(`${BASE}/api/venues/${encodeURIComponent(sport)}${q}`);
  if (!res.ok) return [];
  const data = await res.json();
  return data.venues;
}

export async function createSimulation(config: SimConfig): Promise<SimSummary> {
  const res = await fetchWithRetry(`${BASE}/api/simulations`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(config),
  });
  if (!res.ok) throw new Error(`Create failed: ${res.status}`);
  return res.json();
}

export async function runSimulation(gameId: string): Promise<SimSummary> {
  const res = await fetchWithRetry(`${BASE}/api/simulations/${encodeURIComponent(gameId)}/run`, {
    method: 'POST',
  });
  if (!res.ok) throw new Error(`Run failed: ${res.status}`);
  return res.json();
}

export async function listSimulations(): Promise<SimSummary[]> {
  const res = await fetchWithRetry(`${BASE}/api/simulations`);
  const data = await res.json();
  return data.simulations;
}

export async function getSimulation(gameId: string) {
  const res = await fetchWithRetry(`${BASE}/api/simulations/${encodeURIComponent(gameId)}`);
  if (!res.ok) throw new Error(`Get failed: ${res.status}`);
  return res.json();
}

export async function deleteSimulation(gameId: string): Promise<void> {
  const res = await fetchWithRetry(`${BASE}/api/simulations/${encodeURIComponent(gameId)}`, {
    method: 'DELETE',
  });
  if (!res.ok) throw new Error(`Delete failed: ${res.status}`);
}

export function exportJsonUrl(gameId: string): string {
  return `${BASE}/api/simulations/${encodeURIComponent(gameId)}/export/json`;
}

export function exportCsvUrl(gameId: string): string {
  return `${BASE}/api/simulations/${encodeURIComponent(gameId)}/export/csv`;
}

export async function batchSimulate(config: {
  sport: string;
  n: number;
  seed?: number;
  fidelity?: string;
  home_team?: string | null;
  away_team?: string | null;
  league?: string | null;
}) {
  const res = await fetchWithRetry(`${BASE}/api/simulations/batch`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(config),
  });
  if (!res.ok) throw new Error(`Batch failed: ${res.status}`);
  return res.json();
}

export async function fetchTeamDetail(sport: string, abbr: string, league?: string) {
  const params = new URLSearchParams();
  if (league) params.set('league', league);
  const q = params.toString() ? `?${params.toString()}` : '';
  const res = await fetchWithRetry(`${BASE}/api/teams/${encodeURIComponent(sport)}/${encodeURIComponent(abbr)}${q}`);
  if (!res.ok) throw new Error(`Team not found: ${res.status}`);
  return res.json();
}

export async function fetchPlayerDetail(sport: string, teamAbbr: string, playerId: string, league?: string) {
  const params = new URLSearchParams();
  if (league) params.set('league', league);
  const q = params.toString() ? `?${params.toString()}` : '';
  const res = await fetchWithRetry(`${BASE}/api/players/${encodeURIComponent(sport)}/${encodeURIComponent(teamAbbr)}/${encodeURIComponent(playerId)}${q}`);
  if (!res.ok) throw new Error(`Player not found: ${res.status}`);
  return res.json();
}

/**
 * Open a WebSocket to stream a simulation in real time.
 * Calls `onTick` for every tick message.
 * Auto-reconnects up to 3 times on unexpected disconnects.
 */
export function streamSimulation(
  config: SimConfig,
  onTick: (tick: StreamTick) => void,
  onDone: () => void,
  onError: (err: Event | Error) => void,
): WebSocket {
  let reconnects = 0;
  const MAX_RECONNECTS = 3;
  let finished = false;

  function connect(): WebSocket {
    const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws';
    const ws = new WebSocket(`${protocol}://${window.location.host}/ws/simulate`);

    ws.onopen = () => {
      reconnects = 0;
      ws.send(JSON.stringify(config));
    };

    ws.onmessage = (msg) => {
      const tick: StreamTick = JSON.parse(msg.data);
      onTick(tick);
      if (tick.is_finished) {
        finished = true;
        onDone();
      }
    };

    ws.onerror = (e) => {
      if (!finished) onError(e);
    };

    ws.onclose = (ev) => {
      if (finished) return;
      // Code 1000 = normal close, 1001 = going away — don't reconnect
      if (ev.code === 1000 || ev.code === 1001) {
        onDone();
        return;
      }
      if (reconnects < MAX_RECONNECTS) {
        reconnects++;
        setTimeout(() => {
          Object.assign(currentWs, connect());
        }, 1000 * reconnects);
      } else {
        onError(new Error('WebSocket disconnected after max retries'));
      }
    };

    return ws;
  }

  const currentWs = connect();
  return currentWs;
}
