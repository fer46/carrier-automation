/**
 * NegotiationsTab.tsx -- "Negotiations" tab content showing rate and strategy metrics.
 *
 * This tab helps the team understand how effectively the AI negotiates with
 * carriers.  It is structured in three sections:
 *
 *   1. Summary stat cards (3-column row):
 *      - Avg First Offer  -- the carrier's initial asking rate
 *      - Avg Final Rate   -- the rate ultimately agreed upon
 *      - Avg Rounds       -- how many back-and-forth exchanges per call
 *
 *   2. Charts (2-column grid):
 *      - Rate Progression (LineChart)   -- shows how the average rate evolves
 *        through successive negotiation rounds (initial offer -> round 1 -> final)
 *      - Margin Distribution (BarChart) -- histogram of profit margin buckets
 *        so the team can see where most deals land
 *
 *   3. Strategy Effectiveness (full-width table):
 *      - Compares different negotiation strategies by acceptance rate, average
 *        rounds, and usage count.  Colour-coded: green >= 70%, amber >= 50%, red < 50%.
 */

import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  BarChart, Bar, Cell,
} from 'recharts';
import type { NegotiationsData } from '../types';
import EmptyState from './EmptyState';

// Colour palette for the margin distribution bar chart -- each bucket gets a
// different colour to make them visually distinct.
const COLORS = ['#ef4444', '#f59e0b', '#10b981', '#3b82f6', '#8b5cf6'];

interface Props {
  data: NegotiationsData | null; // null while the initial fetch is still loading
}

export default function NegotiationsTab({ data }: Props) {
  if (!data) return <EmptyState />;

  return (
    <div className="space-y-6">

      {/* ------- Section 1: Key Negotiation Stats (3-column summary cards) ------- */}
      <div className="grid grid-cols-3 gap-4">
        <div className="bg-slate-50 rounded-lg p-4 text-center">
          <p className="text-sm text-slate-500">Avg First Offer</p>
          <p className="text-2xl font-bold text-slate-800">${data.avg_first_offer.toLocaleString()}</p>
        </div>
        <div className="bg-slate-50 rounded-lg p-4 text-center">
          <p className="text-sm text-slate-500">Avg Final Rate</p>
          {/* Green colour signals this is the "good" outcome metric. */}
          <p className="text-2xl font-bold text-emerald-600">${data.avg_final_rate.toLocaleString()}</p>
        </div>
        <div className="bg-slate-50 rounded-lg p-4 text-center">
          <p className="text-sm text-slate-500">Avg Rounds</p>
          <p className="text-2xl font-bold text-slate-800">{data.avg_rounds}</p>
        </div>
      </div>

      {/* ------- Section 2: Charts (Rate Progression + Margin Distribution) ------- */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">

        {/* Rate Progression: tracks how the average negotiated rate changes
            across rounds (e.g. "Initial Offer" -> "Round 1" -> "Final"). */}
        <div className="bg-slate-50 rounded-lg p-4">
          <h3 className="text-sm font-semibold text-slate-700 mb-3">Rate Progression (Avg per Stage)</h3>
          {data.rate_progression.length === 0 ? <EmptyState /> : (
            <ResponsiveContainer width="100%" height={250}>
              <LineChart data={data.rate_progression}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                <XAxis dataKey="round" tick={{ fontSize: 11 }} stroke="#94a3b8" />
                <YAxis tick={{ fontSize: 12 }} stroke="#94a3b8" />
                {/* Dollar-formatted tooltip for rate values.
                    Recharts types `value` as `number | undefined`, so we default to 0. */}
                <Tooltip formatter={(v: number | undefined) => `$${(v ?? 0).toLocaleString()}`} />
                <Line type="monotone" dataKey="avg_rate" stroke="#3b82f6" strokeWidth={2} dot={{ r: 4 }} />
              </LineChart>
            </ResponsiveContainer>
          )}
        </div>

        {/* Margin Distribution: histogram showing how many deals fall into each
            profit margin bucket (e.g. "0-5%", "5-10%", etc.). */}
        <div className="bg-slate-50 rounded-lg p-4">
          <h3 className="text-sm font-semibold text-slate-700 mb-3">Margin Distribution</h3>
          {data.margin_distribution.length === 0 ? <EmptyState /> : (
            <ResponsiveContainer width="100%" height={250}>
              <BarChart data={data.margin_distribution}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                <XAxis dataKey="range" tick={{ fontSize: 12 }} stroke="#94a3b8" />
                <YAxis tick={{ fontSize: 12 }} stroke="#94a3b8" />
                <Tooltip />
                {/* Each bar gets a unique colour from the palette via <Cell>. */}
                <Bar dataKey="count" radius={[4, 4, 0, 0]}>
                  {data.margin_distribution.map((_, i) => (
                    <Cell key={i} fill={COLORS[i % COLORS.length]} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          )}
        </div>
      </div>

    </div>
  );
}
