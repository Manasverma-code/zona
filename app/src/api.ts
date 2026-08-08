import { API_URL } from './config';
import type { Evidence } from './location';
import type {
  AuthResponse,
  DeviceInfo,
  FeedResponse,
  PingResponse,
  Post,
  ServerListResponse,
  Server,
} from './types';

export const OUTSIDE_MESSAGE = "You're outside the zone. Nothing to see.";

export class ApiError extends Error {
  status: number;
  code?: string;

  constructor(status: number, message: string, code?: string) {
    super(message);
    this.status = status;
    this.code = code;
  }
}

interface CallOptions {
  evidence?: Evidence | null;
  token?: string | null;
  emoji?: string | null;
  body?: unknown;
}

async function call<T>(method: string, path: string, opts: CallOptions = {}): Promise<T> {
  const headers: Record<string, string> = {};

  const ev = opts.evidence;
  if (ev && ev.lat != null && ev.lon != null) {
    headers['X-Zona-Lat'] = String(ev.lat);
    headers['X-Zona-Lon'] = String(ev.lon);
    if (ev.fixEpoch != null) headers['X-Zona-Fix-Epoch'] = String(ev.fixEpoch);
    if (ev.accuracy != null) headers['X-Zona-Accuracy-M'] = String(ev.accuracy);
    if (ev.bssidHashes.length > 0) headers['X-Zona-Bssids'] = ev.bssidHashes.join(',');
  }
  if (opts.token) headers.Authorization = `Bearer ${opts.token}`;
  if (opts.emoji) headers['X-Zona-Emoji'] = encodeURIComponent(opts.emoji);

  let res: Response;
  try {
    res = await fetch(`${API_URL}${path}`, {
      method,
      headers,
      body: opts.body != null ? JSON.stringify(opts.body) : undefined,
    });
  } catch {
    throw new ApiError(0, "Can't reach the Zona server. Check your connection.");
  }

  if (!res.ok) {
    let detail: unknown = null;
    try {
      detail = await res.json();
    } catch {
      // non-JSON error body — use the generic message below
    }
    const d = detail as { detail?: unknown } | null;
    const dd = d?.detail;
    if (typeof dd === 'object' && dd != null) {
      const obj = dd as { code?: string; message?: string };
      if (res.status === 403 && obj.code === 'outside_zone') {
        throw new ApiError(403, obj.message ?? OUTSIDE_MESSAGE, 'outside_zone');
      }
      if (obj.message) throw new ApiError(res.status, obj.message);
    }
    if (typeof dd === 'string') throw new ApiError(res.status, dd);
    throw new ApiError(res.status, `Something went wrong (${res.status}).`);
  }

  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

export function register(deviceId: string, evidence: Evidence | null): Promise<AuthResponse> {
  return call<AuthResponse>('POST', '/v1/register', {
    evidence,
    body: { device_id: deviceId },
  });
}

export function ping(token: string, evidence: Evidence | null): Promise<PingResponse> {
  return call<PingResponse>('POST', '/v1/ping', { token, evidence });
}

export function me(token: string): Promise<DeviceInfo> {
  return call<DeviceInfo>('GET', '/v1/me', { token });
}

export function getServers(token: string, evidence: Evidence | null): Promise<ServerListResponse> {
  return call<ServerListResponse>('GET', '/v1/servers', { token, evidence });
}

export function getFeed(
  token: string,
  evidence: Evidence | null,
  serverId?: number
): Promise<FeedResponse> {
  const q = serverId != null ? `?server_id=${serverId}` : '';
  return call<FeedResponse>('GET', `/v1/feed${q}`, { token, evidence });
}

export function createPost(
  token: string,
  evidence: Evidence | null,
  serverId: number,
  body: string
): Promise<Post> {
  return call<Post>('POST', '/v1/posts', {
    token,
    evidence,
    body: { server_id: serverId, body },
  });
}

export function createServer(
  token: string,
  evidence: Evidence | null,
  name: string,
  description: string
): Promise<Server> {
  return call<Server>('POST', '/v1/servers', {
    token,
    evidence,
    body: { name, description },
  });
}

export function react(
  token: string,
  evidence: Evidence | null,
  postId: number,
  emoji: string
): Promise<Post> {
  return call<Post>('POST', `/v1/posts/${postId}/react`, { token, evidence, emoji });
}

export function reportPost(token: string, evidence: Evidence | null, postId: number): Promise<void> {
  return call<void>('POST', `/v1/posts/${postId}/report`, { token, evidence });
}

export function reportServer(
  token: string,
  evidence: Evidence | null,
  serverId: number
): Promise<void> {
  return call<void>('POST', `/v1/servers/${serverId}/report`, { token, evidence });
}

export function deleteServer(
  token: string,
  evidence: Evidence | null,
  serverId: number
): Promise<void> {
  return call<void>('DELETE', `/v1/servers/${serverId}`, { token, evidence });
}
