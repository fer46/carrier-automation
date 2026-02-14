/**
 * App.tsx -- Root component for the Carrier Load Analytics dashboard.
 *
 * This is the single-page application entry point.  It manages:
 *
 *   1. **Global state**: date range filters, active tab, and all five analytics
 *      data slices (summary, operations, negotiations, AI quality, carriers).
 *
 *   2. **Data fetching**: on mount and every POLL_INTERVAL seconds, all five
 *      analytics endpoints are fetched in parallel via Promise.all.  Changing
 *      the date range triggers an immediate re-fetch because `fetchAll` is
 *      memoised with `dateFrom` / `dateTo` as dependencies.
 *
 *   3. **Layout**: three visual regions stacked vertically --
 *        a) Header bar  (branding + date picker + refresh button)
 *        b) KPI hero row (7 summary cards) or an empty-state banner
 *        c) Tabbed content area (Operations | Negotiations | AI Quality | Carriers)
 *
 *   4. **Auto-refresh countdown**: a second timer ticks down every 1s to show
 *      the user when the next automatic data refresh will happen.
 */

import { useState, useEffect, useCallback } from 'react';
import Header from './components/Header';
import KPICard from './components/KPICard';
import OperationsTab from './components/OperationsTab';
import NegotiationsTab from './components/NegotiationsTab';

import CarriersTab from './components/CarriersTab';
import { api } from './api';
import type { SummaryData, OperationsData, NegotiationsData, CarriersData } from './types';

// The four dashboard tabs.  `as const` gives us a literal tuple type so
// `Tab` becomes the union "Operations" | "Negotiations" | "AI Quality" | "Carriers".
const TABS = ['Operations', 'Negotiations', 'Carriers'] as const;
type Tab = typeof TABS[number];

// How often (in seconds) the dashboard automatically re-fetches all data.
const POLL_INTERVAL = 30;

export default function App() {
  // -- UI state --
  const [activeTab, setActiveTab] = useState<Tab>('Operations');
  const [dateFrom, setDateFrom] = useState('');   // ISO date string or empty for "no filter"
  const [dateTo, setDateTo] = useState('');
  const [countdown, setCountdown] = useState(POLL_INTERVAL); // seconds until next auto-refresh

  // -- Data state (one slice per analytics domain, null = not yet loaded) --
  const [summary, setSummary] = useState<SummaryData | null>(null);
  const [operations, setOperations] = useState<OperationsData | null>(null);
  const [negotiations, setNegotiations] = useState<NegotiationsData | null>(null);

  const [carriers, setCarriers] = useState<CarriersData | null>(null);
  const [loading, setLoading] = useState(true);

  /**
   * Fetch all five analytics endpoints in parallel.
   *
   * Memoised on dateFrom/dateTo so that changing the date range automatically
   * triggers a re-fetch via the useEffect below.  Empty date strings are
   * converted to `undefined` so the API client omits them from the query string,
   * causing the backend to return data for the full available range.
   */
  const fetchAll = useCallback(async () => {
    try {
      setLoading(true);
      const from = dateFrom || undefined;
      const to = dateTo || undefined;

      // Fire all five requests concurrently for faster page loads.
      const [s, o, n, c] = await Promise.all([
        api.getSummary(from, to),
        api.getOperations(from, to),
        api.getNegotiations(from, to),
        api.getCarriers(from, to),
      ]);

      setSummary(s);
      setOperations(o);
      setNegotiations(n);
      setCarriers(c);
    } catch (err) {
      // Log but don't crash -- stale data is better than a blank screen.
      console.error('Failed to fetch analytics:', err);
    } finally {
      setLoading(false);
    }
  }, [dateFrom, dateTo]);

  // -- Effect 1: Initial fetch + auto-refresh polling --
  // Runs on mount and whenever fetchAll changes (i.e. when dates change).
  useEffect(() => {
    fetchAll();
    const interval = setInterval(() => {
      fetchAll();
      setCountdown(POLL_INTERVAL); // reset countdown after each auto-refresh
    }, POLL_INTERVAL * 1000);
    return () => clearInterval(interval);
  }, [fetchAll]);

  // -- Effect 2: Countdown ticker (purely cosmetic, ticks every 1 second) --
  useEffect(() => {
    const timer = setInterval(() => {
      setCountdown((c) => (c > 0 ? c - 1 : POLL_INTERVAL));
    }, 1000);
    return () => clearInterval(timer);
  }, []);

  /** Manual refresh: reset the countdown and fetch immediately. */
  const handleRefresh = () => {
    setCountdown(POLL_INTERVAL);
    fetchAll();
  };

  /** Update both date inputs; the useCallback dependency on dateFrom/dateTo
   *  will cause fetchAll to be recreated, triggering the polling effect. */
  const handleDateChange = (from: string, to: string) => {
    setDateFrom(from);
    setDateTo(to);
  };

  // Detect the "zero data" state: the API responded successfully but there
  // are no call records yet.  Show a helpful onboarding message instead of
  // empty charts.
  const isEmpty = summary && summary.total_calls === 0;

  return (
    <div className="min-h-screen bg-slate-100">

      {/* ------- Sticky header with branding, date picker, and refresh ------- */}
      <Header
        dateFrom={dateFrom}
        dateTo={dateTo}
        onDateChange={handleDateChange}
        onRefresh={handleRefresh}
        countdown={countdown}
      />

      <main className="max-w-7xl mx-auto px-6 py-6">

        {/* ------- KPI Hero Row (or empty-state banner) ------- */}
        {isEmpty ? (
          // Onboarding banner: shown when the database has zero call records.
          <div className="bg-white rounded-xl border border-slate-200 p-12 text-center mb-6">
            <p className="text-slate-400 text-lg mb-2">No call data yet</p>
            <p className="text-slate-500 text-sm">
              POST call records to <code className="bg-slate-100 px-2 py-0.5 rounded text-blue-600">/api/analytics/calls</code> to see metrics here.
            </p>
          </div>
        ) : summary ? (
          // KPI hero cards: 7 key metrics displayed in a responsive grid.
          // Responsive breakpoints: 2 cols (mobile) -> 3 cols (tablet) -> 4 cols (desktop).
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4 mb-6">
            <KPICard label="Total Calls" value={summary.total_calls} color="blue" />
            <KPICard label="Acceptance Rate" value={summary.acceptance_rate} format="percent" color="green" />
            <KPICard label="Avg Margin" value={summary.avg_margin_percent} format="percent" color="green" />
            <KPICard label="Avg Duration" value={summary.avg_call_duration} format="duration" color="slate" />
            <KPICard label="Avg Negotiation Rounds" value={summary.avg_negotiation_rounds} color="slate" />
            <KPICard label="Unique Carriers" value={summary.total_carriers} color="blue" />
          </div>
        ) : null /* null = still loading the first fetch; Header shows no cards yet */}

        {/* ------- Tabbed Content Area ------- */}
        <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">

          {/* Tab navigation bar */}
          <div className="border-b border-slate-200">
            <nav className="flex">
              {TABS.map((tab) => (
                <button
                  key={tab}
                  onClick={() => setActiveTab(tab)}
                  className={`px-6 py-3 text-sm font-medium transition-colors ${
                    activeTab === tab
                      ? 'text-blue-600 border-b-2 border-blue-600 bg-blue-50/50'
                      : 'text-slate-500 hover:text-slate-700'
                  }`}
                >
                  {tab}
                </button>
              ))}
            </nav>
          </div>

          {/* Tab content panel -- only the active tab is rendered.
              Shows a loading message on the very first fetch (before summary
              is populated), then switches to the tab components. */}
          <div className="p-6">
            {loading && !summary ? (
              <p className="text-slate-400 text-center py-12">Loading...</p>
            ) : (
              <>
                {activeTab === 'Operations' && <OperationsTab data={operations} />}
                {activeTab === 'Negotiations' && <NegotiationsTab data={negotiations} />}
                {activeTab === 'Carriers' && <CarriersTab data={carriers} />}
              </>
            )}
          </div>
        </div>
      </main>
    </div>
  );
}
