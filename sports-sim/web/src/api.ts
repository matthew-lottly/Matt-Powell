/* API client — REST helpers and WebSocket streaming */

import type { SimConfig, SimSummary, StreamTick } from './types';

const BASE = '';  // proxied by Vite in dev

export async function fetchSports(): Promise<string[]> {
  const res = await fetch(`${BASE}/api/sports`);
  const data = await res.json();
  return data.sports;
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
