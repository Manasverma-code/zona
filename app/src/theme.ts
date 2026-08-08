export const theme = {
  bg: '#0B0B10',
  card: '#16161E',
  cardAlt: '#1D1D28',
  border: '#262636',
  text: '#EDEDF2',
  textDim: '#8B8BA0',
  accent: '#7C5CFF',
  accentSoft: '#2A2345',
  danger: '#FF5C5C',
  success: '#5CFFA8',
  gold: '#FFC75C',
};

export function timeAgo(iso: string): string {
  const then = new Date(iso).getTime();
  const diffSec = Math.max(0, (Date.now() - then) / 1000);
  if (diffSec < 60) return 'just now';
  const min = Math.floor(diffSec / 60);
  if (min < 60) return `${min}m ago`;
  const hr = Math.floor(min / 60);
  if (hr < 24) return `${hr}h ago`;
  return `${Math.floor(hr / 24)}d ago`;
}

export function timeLeft(iso: string): string {
  const then = new Date(iso).getTime();
  const diffSec = Math.max(0, (then - Date.now()) / 1000);
  const min = Math.ceil(diffSec / 60);
  if (min < 60) return `${min}m`;
  const hr = Math.floor(min / 60);
  if (hr < 24) return `${hr}h ${min % 60}m`;
  return `${Math.floor(hr / 24)}d`;
}
