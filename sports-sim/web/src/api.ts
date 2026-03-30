/* API client — REST helpers and WebSocket streaming */

import type { SimConfig, SimSummary, StreamTick, TeamOption, VenueOption } from './types';

const BASE = '';  // proxied by Vite in dev

export async function fetchSports(): Promise<string[]> {
  const res = await fetch(`${BASE}/api/sports`);
  const data = await res.json();
  return data.sports;
}

export async function fetchTeams(sport: string, league?: string, page?: number, per_page?: number): Promise<TeamOption[]> {
  const params = new URLSearchParams();
  if (league) params.set('league', league);
  if (page) params.set('page', String(page));
  if (per_page) params.set('per_page', String(per_page));
  const q = params.toString() ? `?${params.toString()}` : '';
  const res = await fetch(`${BASE}/api/teams/${encodeURIComponent(sport)}${q}`);
  if (!res.ok) return [];
  const data = await res.json();
  return data.teams;
}

export async function fetchLeagues(sport: string): Promise<any[]> {
  const res = await fetch(`${BASE}/api/leagues?sport=${encodeURIComponent(sport)}`);
  if (!res.ok) return [];
  const data = await res.json();
  return data.leagues ?? [];
}

export async function fetchVenues(sport: string, league?: string, page?: number, per_page?: number): Promise<VenueOption[]> {
  const params = new URLSearchParams();
  if (league) params.set('league', league);
  if (page) params.set('page', String(page));
  if (per_page) params.set('per_page', String(per_page));
  const q = params.toString() ? `?${params.toString()}` : '';
  const res = await fetch(`${BASE}/api/venues/${encodeURIComponent(sport)}${q}`);
  if (!res.ok) return [];
  const data = await res.json();
  return data.venues;
}

export async function createSimulation(config: SimConfig): Promise<SimSummary> {
  const res = await fetch(`${BASE}/api/simulations`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(config),
  });
  if (!res.ok) throw new Error(`Create failed: ${res.status}`);
  return res.json();
}

export async function runSimulation(gameId: string): Promise<SimSummary> {
  const res = await fetch(`${BASE}/api/simulations/${encodeURIComponent(gameId)}/run`, {
    method: 'POST',
  });
  if (!res.ok) throw new Error(`Run failed: ${res.status}`);
  return res.json();
}

export async function listSimulations(): Promise<SimSummary[]> {
  const res = await fetch(`${BASE}/api/simulations`);
  const data = await res.json();
  return data.simulations;
}

export async function getSimulation(gameId: string) {
  const res = await fetch(`${BASE}/api/simulations/${encodeURIComponent(gameId)}`);
  if (!res.ok) throw new Error(`Get failed: ${res.status}`);
  return res.json();
}

/**
 * Open a WebSocket to stream a simulation in real time.
 * Calls `onTick` for every tick message.
 */
export function streamSimulation(
  config: SimConfig,
  onTick: (tick: StreamTick) => void,
  onDone: () => void,
  onError: (err: Event | Error) => void,
): WebSocket {
  const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws';
  const ws = new WebSocket(`${protocol}://${window.location.host}/ws/simulate`);

  ws.onopen = () => {
    ws.send(JSON.stringify(config));
  };

  ws.onmessage = (msg) => {
    const tick: StreamTick = JSON.parse(msg.data);
    onTick(tick);
    if (tick.is_finished) {
      onDone();
    }
  };

  ws.onerror = (e) => onError(e);
  ws.onclose = () => onDone();

  return ws;
}
