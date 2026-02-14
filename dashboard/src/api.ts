/**
 * api.ts -- Thin HTTP client for the Carrier Load Analytics backend.
 *
 * All requests target /api/analytics/* endpoints which are proxied by the Vite
 * dev server (see vite.config.ts) during development, and served directly by
 * FastAPI in production.
 *
 * Authentication is handled via the X-API-Key header.  The key is read from
 * the VITE_API_KEY environment variable (set in .env or at build time).
 *
 * Every endpoint accepts optional `from` / `to` date strings (ISO format) for
 * filtering the analytics window.  Empty strings are stripped so the backend
 * returns data for the full available range when no dates are specified.
 */

import type {
  SummaryData,
  OperationsData,
  NegotiationsData,
  AIQualityData,
  CarriersData,
} from './types';

// Read the API key from Vite environment variables (prefixed with VITE_ to be
// exposed to the client bundle).  Falls back to empty string for local dev
// where the key may not be required.
const API_KEY = import.meta.env.VITE_API_KEY || '';

// Base path shared by all analytics endpoints.
const BASE = '/api/analytics';

/**
 * Generic fetch wrapper with automatic JSON parsing and error handling.
 *
 * @typeParam T - The expected response body shape (one of our analytics types).
 * @param path   - The API path relative to the origin (e.g. "/api/analytics/summary").
 * @param params - Optional query parameters; falsy values are silently omitted
 *                 so callers can pass empty strings without polluting the URL.
 * @throws Error if the HTTP response status is not 2xx.
 */
async function fetchAPI<T>(path: string, params?: Record<string, string>): Promise<T> {
  // Build a fully-qualified URL so we can safely append query params.
  const url = new URL(path, window.location.origin);

  // Attach only non-empty query parameters (avoids sending "?from=&to=").
  if (params) {
    Object.entries(params).forEach(([k, v]) => {
      if (v) url.searchParams.set(k, v);
    });
  }

  const res = await fetch(url.toString(), {
    headers: { 'X-API-Key': API_KEY },
  });

  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}

/**
 * Exported API client object.
 *
 * Each method corresponds to one backend analytics endpoint and returns a
 * strongly-typed Promise.  The `from` / `to` parameters are optional date
 * strings (e.g. "2025-01-01") used to filter the analytics window.
 */
export const api = {
  /** Fetch high-level KPI summary (total calls, acceptance rate, etc.). */
  getSummary: (from?: string, to?: string) =>
    fetchAPI<SummaryData>(`${BASE}/summary`, { from: from || '', to: to || '' }),

  /** Fetch operational metrics (call volume, outcomes, durations, rejections). */
  getOperations: (from?: string, to?: string) =>
    fetchAPI<OperationsData>(`${BASE}/operations`, { from: from || '', to: to || '' }),

  /** Fetch negotiation metrics (rate progression, margins, strategy comparison). */
  getNegotiations: (from?: string, to?: string) =>
    fetchAPI<NegotiationsData>(`${BASE}/negotiations`, { from: from || '', to: to || '' }),

  /** Fetch AI quality metrics (compliance, violations, interruptions, tone). */
  getAIQuality: (from?: string, to?: string) =>
    fetchAPI<AIQualityData>(`${BASE}/ai-quality`, { from: from || '', to: to || '' }),

  /** Fetch carrier-focused metrics (sentiment, engagement, objections, leaderboard). */
  getCarriers: (from?: string, to?: string) =>
    fetchAPI<CarriersData>(`${BASE}/carriers`, { from: from || '', to: to || '' }),
};
