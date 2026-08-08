export interface GateStatus {
  inside: boolean;
  reason: string | null;
}

export interface AuthResponse {
  token: string;
  handle: string;
  gate: GateStatus;
}

export interface PingResponse {
  gate: GateStatus;
  handle: string;
  streak: number;
}

export interface Post {
  id: number;
  server_id: number;
  body: string;
  handle: string;
  created_at: string;
  expires_at: string;
  reactions: Record<string, number>;
  my_reaction: string | null;
}

export interface FeedResponse {
  posts: Post[];
  post_count: number;
  streak: number;
}

export interface Server {
  id: number;
  name: string;
  description: string;
  post_count: number;
  is_default: boolean;
  created_at: string;
  is_creator: boolean;
}

export interface ServerListResponse {
  servers: Server[];
  count: number;
}

export interface DeviceInfo {
  handle: string;
  streak: number;
}
