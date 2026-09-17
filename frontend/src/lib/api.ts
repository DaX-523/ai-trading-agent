export type TradingMode = "SANDBOX" | "TESTNET" | "LIVE";
export type AppView = "dashboard" | "leaderboard" | "models";

export const BACKEND_URL = "http://localhost:3000";
export const ADMIN_TOKEN_STORAGE_KEY = "adminApiToken";

export function getAdminToken(): string {
  try {
    return localStorage.getItem(ADMIN_TOKEN_STORAGE_KEY) ?? "";
  } catch {
    return "";
  }
}

export function setAdminToken(token: string): void {
  localStorage.setItem(ADMIN_TOKEN_STORAGE_KEY, token);
}

export function clearAdminToken(): void {
  localStorage.removeItem(ADMIN_TOKEN_STORAGE_KEY);
}

export async function apiFetch(path: string, init: RequestInit = {}): Promise<Response> {
  const headers = new Headers(init.headers);
  const token = getAdminToken();
  if (token && !headers.has("X-Admin-Token")) {
    headers.set("X-Admin-Token", token);
  }
  return fetch(`${BACKEND_URL}${path}`, { ...init, headers });
}
