const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || "/api/v1").replace(/\/+$/, "");
const TOKEN_KEY = "kairos.access_token";
let refreshInFlight: Promise<AuthResponse | null> | null = null;

export interface KairosAccount {
  id: string;
  email: string;
  full_name: string;
  phone_number: string | null;
  is_active: boolean;
  /** Backward-compatible alias for email verification only. */
  is_verified: boolean;
  email_verified: boolean;
  identity_verified: boolean;
  last_login_at: string | null;
  roles: string[];
}

export interface AuthResponse {
  access_token: string;
  token_type: "bearer";
  expires_in: number;
  account: KairosAccount;
}

export interface ApiValidationError {
  loc: Array<string | number>;
  msg: string;
  type?: string;
}

export class ApiError extends Error {
  status: number;
  validationErrors: ApiValidationError[];
  constructor(message: string, status: number, validationErrors: ApiValidationError[] = []) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.validationErrors = validationErrors;
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

export async function refreshSession(): Promise<AuthResponse | null> {
  if (refreshInFlight) return refreshInFlight;
  refreshInFlight = (async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/auth/refresh`, {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
      });
      if (!response.ok) {
        clearAccessToken();
        return null;
      }
      const result = await response.json() as AuthResponse;
      setAccessToken(result.access_token);
      return result;
    } catch {
      return null;
    } finally {
      refreshInFlight = null;
    }
  })();
  return refreshInFlight;
}

const AUTH_BROADCAST = "kairos-auth-session";
function announceLogout(): void {
  if (typeof BroadcastChannel !== "undefined") {
    const channel = new BroadcastChannel(AUTH_BROADCAST);
    channel.postMessage({ type: "logout" });
    channel.close();
  }
}

export function subscribeToSessionLogout(onLogout: () => void): () => void {
  if (typeof BroadcastChannel === "undefined") return () => undefined;
  const channel = new BroadcastChannel(AUTH_BROADCAST);
  channel.onmessage = (event: MessageEvent) => {
    if (event.data?.type === "logout") {
      clearAccessToken();
      onLogout();
    }
  };
  return () => channel.close();
}

function accessTokenExpiresSoon(token: string | null): boolean {
  if (!token) return false;
  try {
    const payload = token.split(".")[1];
    if (!payload) return false;
    const normalized = payload.replace(/-/g, "+").replace(/_/g, "/");
    const claims = JSON.parse(window.atob(normalized)) as { exp?: number };
    return typeof claims.exp === "number" && claims.exp * 1000 - Date.now() <= 120_000;
  } catch {
    return false;
  }
}

export async function apiRequest<T>(
  path: string,
  init: RequestInit = {},
): Promise<T> {
  const isSessionEndpoint = /\/auth\/(login|refresh|logout)(?:$|\?)/.test(path);
  if (!isSessionEndpoint && accessTokenExpiresSoon(getAccessToken())) {
    await refreshSession();
  }
  const headers = new Headers(init.headers);
  if (init.body && !(init.body instanceof FormData) && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  const token = getAccessToken();
  if (token && !headers.has("Authorization")) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  const requestUrl = `${API_BASE_URL}${path.startsWith("/") ? path : `/${path}`}`;
  let response = await fetch(requestUrl, { ...init, headers, credentials: "include" });
  if (response.status === 401 && !isSessionEndpoint) {
    const renewed = await refreshSession();
    if (renewed) {
      headers.set("Authorization", `Bearer ${renewed.access_token}`);
      response = await fetch(requestUrl, { ...init, headers, credentials: "include" });
    } else {
      clearAccessToken();
    }
  }

  if (!response.ok) {
    if (response.status === 401 && !isSessionEndpoint) clearAccessToken();
    let message = `Request failed (${response.status})`;
    let validationErrors: ApiValidationError[] = [];
    try {
      const payload = await response.json() as { detail?: unknown; error?: { message?: string } };
      if (typeof payload.detail === "string") message = payload.detail;
      else if (Array.isArray(payload.detail)) {
        const details = payload.detail as ApiValidationError[];
        validationErrors = details.filter((item) => item && Array.isArray(item.loc) && typeof item.msg === "string");
        message = details.map((item) => {
          const location = Array.isArray(item.loc) ? item.loc.filter((part) => part !== "body").join(". ") : "";
          return location ? `${location}: ${item.msg}` : item.msg;
        }).filter(Boolean).join(". ") || message;
      } else if (payload.error?.message) message = payload.error.message;
    } catch {
      // Keep the status-based message when the response is not JSON.
    }
    throw new ApiError(message, response.status, validationErrors);
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
  const token = getAccessToken();
  clearAccessToken();
  announceLogout();

  // Revoke the server-side token version when possible, but never keep the
  // browser session alive just because the API is temporarily unavailable.
  if (token) {
    void fetch(`${API_BASE_URL}/auth/logout`, {
      method: "POST",
      credentials: "include",
      headers: { Authorization: `Bearer ${token}` },
    }).catch(() => {
      // Local logout has already completed; network failure must not restore the session.
    });
  }
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

export async function downloadApiFile(path: string, filename: string): Promise<void> {
  const headers = new Headers();
  const token = getAccessToken();
  if (token) headers.set("Authorization", `Bearer ${token}`);
  const response = await fetch(`${API_BASE_URL}${path.startsWith("/") ? path : `/${path}`}`, { headers, credentials: "include" });
  if (!response.ok) {
    if (response.status === 401) clearAccessToken();
    throw new ApiError(`Download failed (${response.status})`, response.status);
  }
  const blob = await response.blob();
  const objectUrl = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = objectUrl;
  anchor.download = filename;
  anchor.style.display = "none";
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  window.setTimeout(() => URL.revokeObjectURL(objectUrl), 1000);
}
