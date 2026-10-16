/**
 * Thin API client. Every request that needs auth attaches the bearer
 * token from localStorage; the backend is the only place that decides
 * what a given role is allowed to see. 403s from HR routes are handled by
 * callers, since the server is the real gate.
 *
 * URLs are same-origin by default: in dev the Vite server proxies /api
 * and /ws to the backend (vite.config.js), and in production the backend
 * serves this built app itself. Set VITE_API_BASE only if the API lives
 * on a different origin.
 */
const API_BASE = import.meta.env.VITE_API_BASE ?? "";

const TOKEN_KEY = "smiley_token";

export const session = {
  get: () => localStorage.getItem(TOKEN_KEY),
  set: (token) => localStorage.setItem(TOKEN_KEY, token),
  clear: () => localStorage.removeItem(TOKEN_KEY),
};

// Fired on any 401 from an authenticated call (expired/revoked session),
// so App can drop back to the login screen instead of silently failing.
export const UNAUTHORIZED_EVENT = "smiley:unauthorized";

async function request(path, options = {}) {
  const token = session.get();
  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(options.headers || {}),
    },
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    if (res.status === 401 && path !== "/api/auth/login") {
      window.dispatchEvent(new Event(UNAUTHORIZED_EVENT));
    }
    const detail = Array.isArray(body.detail) ? "Please check your input." : body.detail;
    const err = new Error(detail || `Request failed (${res.status})`);
    err.status = res.status;
    throw err;
  }
  if (res.status === 204) return null;
  return res.json();
}

export const api = {
  health: () => request("/api/health"),

  login: (username, password) =>
    request("/api/auth/login", { method: "POST", body: JSON.stringify({ username, password }) }),
  logout: () => request("/api/auth/logout", { method: "POST" }),

  getMe: () => request("/api/me"),

  // true/false rather than throwing: a 403 here is an expected answer
  // ("you're not hr_admin"), not an error.
  verifyHrAccess: async () => {
    try {
      await request("/api/hr/verify");
      return true;
    } catch {
      return false;
    }
  },
};
