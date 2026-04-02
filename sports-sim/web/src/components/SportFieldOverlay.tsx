import { getSportPresentation } from '../sportPresentation';
import type { SportType, StreamTick } from '../types';

interface Props {
  sport: SportType;
  tick: StreamTick | null;
}

type Point = { x: number; y: number };

function clamp(value: number, min: number, max: number): number {
  return Math.max(min, Math.min(max, value));
}

function orbit(progress: number, cx: number, cy: number, rx: number, ry: number): Point {
  const angle = progress * Math.PI * 2;
  return {
    x: cx + Math.cos(angle) * rx,
    y: cy + Math.sin(angle) * ry,
  };
}

function progressFromTick(tick: StreamTick): number {
  return (tick.clock * 0.03 + tick.period * 0.17 + tick.home_score * 0.11 + tick.away_score * 0.07) % 1;
}

export default function SportFieldOverlay({ sport, tick }: Props) {
  if (!tick) {
    return null;
  }

  const presentation = getSportPresentation(sport);
  const progress = progressFromTick(tick);
  const momentumDelta = tick.home_momentum - tick.away_momentum;
  const eventLabel = tick.events[tick.events.length - 1]?.type ?? presentation.keyMoments[0] ?? presentation.label;

  const renderSharedPulse = (point: Point, color = '#f8fafc') => (
    <>
      <circle cx={point.x} cy={point.y} r="2.2" fill={color} className="overlay-pulse" />
      <circle cx={point.x} cy={point.y} r="0.9" fill={color} className="overlay-core" />
    </>
  );

  if (sport === 'racing') {
    const homeCar = orbit(progress, 50, 50, 34, 18);
    const awayCar = orbit((progress + 0.18) % 1, 50, 50, 28, 14);
    return (
      <svg viewBox="0 0 100 100" className="absolute inset-0 h-full w-full pointer-events-none" aria-hidden="true">
        <path d="M 16 50 a 34 18 0 1 1 68 0 a 34 18 0 1 1 -68 0" fill="none" stroke="rgba(255,255,255,0.12)" strokeWidth="1" className="overlay-dash" />
        <path d="M 22 50 a 28 14 0 1 1 56 0 a 28 14 0 1 1 -56 0" fill="none" stroke="rgba(255,255,255,0.08)" strokeWidth="0.8" />
        <rect x={homeCar.x - 2.2} y={homeCar.y - 1.2} width="4.4" height="2.4" rx="0.8" fill="#60a5fa" className="overlay-drift-a" />
        <rect x={awayCar.x - 2.2} y={awayCar.y - 1.2} width="4.4" height="2.4" rx="0.8" fill="#f87171" className="overlay-drift-b" />
        <text x="50" y="14" textAnchor="middle" className="overlay-label">{humanize(eventLabel)}</text>
      </svg>
    );
  }

  if (sport === 'golf') {
    const ball = { x: 18 + progress * 62, y: 54 - Math.sin(progress * Math.PI) * 10 };
    return (
      <svg viewBox="0 0 100 100" className="absolute inset-0 h-full w-full pointer-events-none" aria-hidden="true">
        <path d="M 16 60 Q 42 30 82 48" fill="none" stroke="rgba(255,255,255,0.18)" strokeWidth="1" strokeDasharray="2 3" className="overlay-dash" />
        <circle cx="82" cy="48" r="4.5" fill="rgba(34,197,94,0.12)" stroke="rgba(34,197,94,0.35)" />
        {renderSharedPulse(ball)}
        <text x="50" y="16" textAnchor="middle" className="overlay-label">Approach line</text>
      </svg>
    );
  }

  if (sport === 'football') {
    const line = clamp(50 + momentumDelta * 22 + Math.sin(progress * Math.PI * 2) * 16, 18, 82);
    const firstDown = clamp(line + 10, 24, 88);
    return (
      <svg viewBox="0 0 100 100" className="absolute inset-0 h-full w-full pointer-events-none" aria-hidden="true">
        <line x1={line} y1="18" x2={line} y2="82" stroke="rgba(96,165,250,0.65)" strokeWidth="1.2" className="overlay-pulse-line" />
        <line x1={firstDown} y1="18" x2={firstDown} y2="82" stroke="rgba(251,191,36,0.65)" strokeWidth="1.2" className="overlay-pulse-line" />
        <rect x={line - 2} y="47" width="4" height="6" rx="1.5" fill="#60a5fa" className="overlay-drift-a" />
        <text x="50" y="14" textAnchor="middle" className="overlay-label">Drive leverage</text>
      </svg>
    );
  }

  if (sport === 'baseball') {
    const pitchX = 50 + Math.sin(progress * Math.PI * 2) * 6;
    return (
      <svg viewBox="0 0 100 100" className="absolute inset-0 h-full w-full pointer-events-none" aria-hidden="true">
        <path d="M 50 58 Q 52 48 50 38" fill="none" stroke="rgba(255,255,255,0.18)" strokeWidth="1" strokeDasharray="2 2" className="overlay-dash" />
        {renderSharedPulse({ x: pitchX, y: 46 })}
        <circle cx="40" cy="55" r={tick.home_score % 2 === 1 ? '1.8' : '1'} fill="#60a5fa" opacity={tick.home_score % 2 === 1 ? '0.8' : '0.2'} />
        <circle cx="50" cy="45" r={tick.home_score + tick.away_score > 0 ? '1.8' : '1'} fill="#f8fafc" opacity={tick.home_score + tick.away_score > 0 ? '0.8' : '0.2'} />
        <circle cx="60" cy="55" r={tick.away_score % 2 === 1 ? '1.8' : '1'} fill="#f87171" opacity={tick.away_score % 2 === 1 ? '0.8' : '0.2'} />
        <text x="50" y="14" textAnchor="middle" className="overlay-label">At-bat pressure</text>
      </svg>
    );
  }

  if (sport === 'tennis') {
    const ball = { x: 50 + Math.sin(progress * Math.PI * 2) * 18, y: 50 + Math.cos(progress * Math.PI * 2) * 28 };
    return (
      <svg viewBox="0 0 100 100" className="absolute inset-0 h-full w-full pointer-events-none" aria-hidden="true">
        <circle cx="50" cy="20" r="2" fill="#60a5fa" className="overlay-drift-a" />
        <circle cx="50" cy="80" r="2" fill="#f87171" className="overlay-drift-b" />
        <path d="M 50 20 Q 64 50 50 80" fill="none" stroke="rgba(255,255,255,0.14)" strokeWidth="1" strokeDasharray="2 3" className="overlay-dash" />
        {renderSharedPulse(ball, '#fde047')}
        <text x="50" y="14" textAnchor="middle" className="overlay-label">Rally shape</text>
      </svg>
    );
  }

  if (sport === 'boxing' || sport === 'mma') {
    const offset = 10 + Math.sin(progress * Math.PI * 2) * 4;
    return (
      <svg viewBox="0 0 100 100" className="absolute inset-0 h-full w-full pointer-events-none" aria-hidden="true">
        <circle cx={50 - offset} cy="50" r="3.2" fill="#60a5fa" className="overlay-drift-a" />
        <circle cx={50 + offset} cy="50" r="3.2" fill="#f87171" className="overlay-drift-b" />
        <circle cx="50" cy="50" r="10" fill="none" stroke="rgba(255,255,255,0.08)" strokeWidth="1" className="overlay-pulse-ring" />
        <text x="50" y="14" textAnchor="middle" className="overlay-label">Range battle</text>
      </svg>
    );
  }

  if (sport === 'cricket') {
    const ball = { x: 50 + Math.sin(progress * Math.PI * 2) * 2, y: 34 + progress * 26 };
    return (
      <svg viewBox="0 0 100 100" className="absolute inset-0 h-full w-full pointer-events-none" aria-hidden="true">
        <circle cx="50" cy="50" r="26" fill="none" stroke="rgba(255,255,255,0.1)" strokeWidth="1" strokeDasharray="2 3" className="overlay-dash" />
        <line x1="50" y1="32" x2="50" y2="68" stroke="rgba(255,255,255,0.18)" strokeWidth="1" />
        {renderSharedPulse(ball, '#fde047')}
        <text x="50" y="14" textAnchor="middle" className="overlay-label">Bowling line</text>
      </svg>
    );
  }

  if (sport === 'hockey') {
    const puck = { x: 50 + momentumDelta * 14 + Math.sin(progress * Math.PI * 2) * 14, y: 50 + Math.cos(progress * Math.PI * 2) * 10 };
    return (
      <svg viewBox="0 0 100 100" className="absolute inset-0 h-full w-full pointer-events-none" aria-hidden="true">
        <rect x="24" y="28" width="52" height="44" rx="20" fill="none" stroke="rgba(255,255,255,0.08)" strokeWidth="1" />
        {renderSharedPulse(puck, '#e2e8f0')}
        <circle cx="34" cy="50" r="2" fill="#60a5fa" className="overlay-drift-a" />
        <circle cx="66" cy="50" r="2" fill="#f87171" className="overlay-drift-b" />
        <text x="50" y="14" textAnchor="middle" className="overlay-label">Ice tilt</text>
      </svg>
    );
  }

  if (sport === 'basketball') {
    const ball = { x: 50 + Math.sin(progress * Math.PI * 2) * 24, y: 50 + Math.cos(progress * Math.PI * 2) * 18 };
    return (
      <svg viewBox="0 0 100 100" className="absolute inset-0 h-full w-full pointer-events-none" aria-hidden="true">
        <circle cx="26" cy="50" r="10" fill="none" stroke="rgba(255,255,255,0.08)" strokeWidth="1" />
        <circle cx="74" cy="50" r="10" fill="none" stroke="rgba(255,255,255,0.08)" strokeWidth="1" />
        <path d="M 26 50 Q 50 34 74 50" fill="none" stroke="rgba(255,255,255,0.14)" strokeWidth="1" strokeDasharray="3 3" className="overlay-dash" />
        {renderSharedPulse(ball, '#fb923c')}
        <text x="50" y="14" textAnchor="middle" className="overlay-label">Shot creation</text>
      </svg>
    );
  }

  if (sport === 'soccer') {
    const ball = { x: 50 + momentumDelta * 18 + Math.sin(progress * Math.PI * 2) * 10, y: 50 + Math.cos(progress * Math.PI * 2) * 16 };
    return (
      <svg viewBox="0 0 100 100" className="absolute inset-0 h-full w-full pointer-events-none" aria-hidden="true">
        <line x1="50" y1="18" x2="50" y2="82" stroke="rgba(255,255,255,0.08)" strokeWidth="1" />
        <path d="M 18 50 C 28 40, 38 40, 50 50" fill="none" stroke="rgba(96,165,250,0.18)" strokeWidth="1.2" className="overlay-dash" />
        <path d="M 82 50 C 72 60, 62 60, 50 50" fill="none" stroke="rgba(248,113,113,0.18)" strokeWidth="1.2" className="overlay-dash" />
        {renderSharedPulse(ball)}
        <text x="50" y="14" textAnchor="middle" className="overlay-label">Territory swing</text>
      </svg>
    );
  }

  const defaultPoint = { x: 50 + Math.sin(progress * Math.PI * 2) * 16, y: 50 + Math.cos(progress * Math.PI * 2) * 16 };
  return (
    <svg viewBox="0 0 100 100" className="absolute inset-0 h-full w-full pointer-events-none" aria-hidden="true">
      {renderSharedPulse(defaultPoint)}
      <text x="50" y="14" textAnchor="middle" className="overlay-label">{humanize(eventLabel)}</text>
    </svg>
  );
}

function humanize(value: string): string {
  return value.replace(/_/g, ' ');
}