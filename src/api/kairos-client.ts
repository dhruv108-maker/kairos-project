const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || "/api/v1").replace(/\/+$/, "");
const TOKEN_KEY = "kairos.access_token";

export interface KairosAccount {
  id: string;
  email: string;
  full_name: string;
  phone_number: string | null;
  is_active: boolean;
  is_verified: boolean;
  last_login_at: string | null;
  roles: string[];
}

export interface AuthResponse {
  access_token: string;
  token_type: "bearer";
  expires_in: number;
  account: KairosAccount;
}

export class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

export function getAccessToken(): string | null {
  return window.sessionStorage.getItem(TOKEN_KEY);
}

export function setAccessToken(token: string): void {
  window.sessionStorage.setItem(TOKEN_KEY, token);
}

export function clearAccessToken(): void {
  window.sessionStorage.removeItem(TOKEN_KEY);
}

export async function apiRequest<T>(
  path: string,
  init: RequestInit = {},
): Promise<T> {
  const headers = new Headers(init.headers);
  if (init.body && !(init.body instanceof FormData) && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  const token = getAccessToken();
  if (token && !headers.has("Authorization")) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  const response = await fetch(`${API_BASE_URL}${path.startsWith("/") ? path : `/${path}`}`, {
    ...init,
    headers,
  });

  if (!response.ok) {
    if (response.status === 401) clearAccessToken();
    let message = `Request failed (${response.status})`;
    try {
      const payload = await response.json() as { detail?: unknown; error?: { message?: string } };
      if (typeof payload.detail === "string") message = payload.detail;
      else if (Array.isArray(payload.detail)) {
        message = payload.detail.map((item: { msg?: string }) => item.msg).filter(Boolean).join(". ") || message;
      } else if (payload.error?.message) message = payload.error.message;
    } catch {
      // Keep the status-based message when the response is not JSON.
    }
    throw new ApiError(message, response.status);
  }

  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

export async function signIn(email: string, password: string): Promise<AuthResponse> {
  const result = await apiRequest<AuthResponse>("/auth/login", {
    method: "POST",
    body: JSON.stringify({ email: email.trim().toLowerCase(), password }),
  });
  setAccessToken(result.access_token);
  return result;
}

export function getCurrentAccount(): Promise<KairosAccount> {
  return apiRequest<KairosAccount>("/auth/me");
}

export function signOut(): void {
  clearAccessToken();
}

export async function getRoleDashboard(account: KairosAccount): Promise<unknown> {
  const roles = account.roles.map((role) => role.toUpperCase());
  if (roles.includes("STUDENT")) return apiRequest("/students/me/dashboard");
  if (roles.includes("FACULTY")) return apiRequest("/faculty/me/dashboard");

  // The institution ID is resolved from the authenticated user's permitted institutions.
  try {
    const result = await apiRequest<{ items: Array<{ id: string }> }>("/institutions");
    const institutionId = result.items?.[0]?.id;
    if (!institutionId) return null;
    return await apiRequest(`/institutions/${encodeURIComponent(institutionId)}/dashboard`);
  } catch (error) {
    if (error instanceof ApiError && error.status === 403) return null;
    throw error;
  }
}
