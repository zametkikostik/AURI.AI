const API_BASE =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("auri_access_token");
}

export function setTokens(access: string, refresh?: string) {
  localStorage.setItem("auri_access_token", access);
  if (refresh) localStorage.setItem("auri_refresh_token", refresh);
}

export function clearTokens() {
  localStorage.removeItem("auri_access_token");
  localStorage.removeItem("auri_refresh_token");
}

async function request<T>(
  path: string,
  options: RequestInit = {},
  auth = true
): Promise<T> {
  const headers: Record<string, string> = {
    ...(options.headers as Record<string, string>),
  };

  if (!(options.body instanceof FormData)) {
    headers["Content-Type"] = headers["Content-Type"] || "application/json";
  }

  if (auth) {
    const token = getToken();
    if (token) headers["Authorization"] = `Bearer ${token}`;
  }

  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers,
    cache: "no-store",
  });

  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`API ${res.status}: ${text || res.statusText}`);
  }

  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

export type Meeting = {
  id: string;
  title: string;
  description?: string | null;
  status: string;
  source: string;
  language: string;
  is_private: boolean;
  duration_seconds?: number | null;
  executive_summary?: string | null;
  topics?: string[] | null;
  action_items?: unknown[] | null;
  created_at: string;
  updated_at: string;
};

export type MeetingDetail = Meeting & {
  recordings: Array<{
    id: string;
    status: string;
    original_filename?: string | null;
    duration_seconds?: number | null;
    content_type: string;
    created_at: string;
  }>;
  transcript?: {
    id: string;
    full_text: string;
    language?: string | null;
    provider: string;
    status: string;
    speakers?: unknown[] | null;
  } | null;
};

export const api = {
  health: () =>
    request<{ status: string; ai_mode: string }>("/health", {}, false),

  register: (data: {
    email: string;
    password: string;
    full_name?: string;
    organization_name: string;
  }) =>
    request<{ access_token: string; refresh_token: string }>(
      "/api/v1/auth/register",
      { method: "POST", body: JSON.stringify(data) },
      false
    ),

  login: (email: string, password: string) =>
    request<{ access_token: string; refresh_token: string }>(
      "/api/v1/auth/login",
      { method: "POST", body: JSON.stringify({ email, password }) },
      false
    ),

  me: () =>
    request<{
      user: { id: string; email: string; full_name?: string; role: string };
      organization: { id: string; name: string; plan: string; ai_mode: string };
    }>("/api/v1/auth/me"),

  listMeetings: (page = 1) =>
    request<{ items: Meeting[]; total: number; page: number; page_size: number }>(
      `/api/v1/meetings?page=${page}`
    ),

  getMeeting: (id: string) =>
    request<MeetingDetail>(`/api/v1/meetings/${id}`),

  createMeeting: (data: {
    title: string;
    language?: string;
    description?: string;
  }) =>
    request<Meeting>("/api/v1/meetings", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  semanticSearch: (query: string, limit = 10) =>
    request<{ query: string; results: unknown[]; count: number }>(
      "/api/v1/search/semantic",
      { method: "POST", body: JSON.stringify({ query, limit }) }
    ),

  hybridSearch: (query: string, limit = 10) =>
    request<{ query: string; semantic: unknown[]; keyword: unknown[] }>(
      "/api/v1/search/hybrid",
      { method: "POST", body: JSON.stringify({ query, limit }) }
    ),

  getMeetingKnowledge: (id: string) =>
    request<Record<string, unknown>>(`/api/v1/knowledge/meetings/${id}`),

  listTopics: () =>
    request<{ topics: Array<{ name: string; count: number }> }>(
      "/api/v1/knowledge/topics"
    ),
};
