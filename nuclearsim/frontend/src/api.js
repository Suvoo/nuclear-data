// Central API base URL resolver.
//
// In development (`npm run dev`) we use an empty base so the Vite proxy in
// vite.config.js forwards /api/* to http://localhost:8000.
//
// In production builds, set VITE_API_BASE at build time to point at the
// public URL of your backend, e.g.:
//
//   VITE_API_BASE="https://nuclearsim.yourtunnel.trycloudflare.com" npm run build
//
// If VITE_API_BASE is unset the frontend falls back to same-origin (useful
// when FastAPI is serving the static build itself).
export const API_BASE = (import.meta.env.VITE_API_BASE || "").replace(/\/$/, "");

export const api = (path) => `${API_BASE}${path}`;
