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
 *      - Negotiation Outcomes (PieChart donut) -- shows what happens when the AI
 *        talks to carriers: accepted at first offer, negotiated & agreed, or no deal
 *      - Margin Distribution (BarChart) -- histogram of profit margin buckets
 *        so the team can see where most deals land
 *
 *   3. Strategy Effectiveness (full-width table):
 *      - Compares different negotiation strategies by acceptance rate, average
 *        rounds, and usage count.  Colour-coded: green >= 70%, amber >= 50%, red < 50%.
 */

import {
  PieChart, Pie, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  BarChart, Bar, Cell,
} from 'recharts';
import type { NegotiationsData } from '../types';
import EmptyState from './EmptyState';

// Colour palette for the margin distribution bar chart -- each bucket gets a
// different colour to make them visually distinct.
const COLORS = ['#f43f5e', '#f97316', '#22c55e', '#3b82f6', '#a855f7'];

// Semantic colours for the negotiation outcomes donut chart.
const OUTCOME_COLORS: Record<string, string> = {
  'Accepted at First Offer': '#22c55e',  // green
  'Negotiated & Agreed': '#3b82f6',       // blue
  'No Deal': '#f43f5e',                   // rose
};

interface Props {
  data: NegotiationsData | null; // null while the initial fetch is still loading
}

export default function NegotiationsTab({ data }: Props) {
  if (!data) return <EmptyState />;

  const total = data.negotiation_outcomes.reduce((s, d) => s + d.count, 0);

  return (
    <div className="space-y-6">

      {/* ------- Section 1: Key Negotiation Stats (3-column summary cards) ------- */}
      <div className="grid grid-cols-3 gap-4">
        <div className="bg-emerald-50 rounded-lg p-4 text-center">
          <p className="text-sm text-emerald-600/70">Avg Savings / Deal</p>
          <p className="text-2xl font-bold text-emerald-700">${data.avg_savings.toLocaleString()}</p>
        </div>
        <div className="bg-emerald-50 rounded-lg p-4 text-center">
          <p className="text-sm text-emerald-600/70">Avg Savings %</p>
          <p className="text-2xl font-bold text-emerald-700">{data.avg_savings_percent}%</p>
        </div>
        <div className="bg-gray-50 rounded-lg p-4 text-center">
          <p className="text-sm text-gray-400">Avg Rounds</p>
          <p className="text-2xl font-bold text-black">{data.avg_rounds}</p>
        </div>
      </div>

      {/* ------- Section 2: Charts (Rate Progression + Margin Distribution) ------- */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">

        {/* Negotiation Outcomes: donut chart showing what happens when the AI
            talks to carriers — accepted at first offer, negotiated, or no deal. */}
        <div className="bg-gray-50 rounded-lg p-4">
          <h3 className="text-sm font-semibold text-gray-700 mb-3">Negotiation Outcomes</h3>
          {total === 0 ? <EmptyState /> : (
            <>
              <ResponsiveContainer width="100%" height={200}>
                <PieChart>
                  <Pie data={data.negotiation_outcomes} cx="50%" cy="50%" innerRadius={55} outerRadius={85}
                       dataKey="count" nameKey="name">
                    {data.negotiation_outcomes.map((entry, i) => (
                      <Cell key={i} fill={OUTCOME_COLORS[entry.name] || COLORS[i % COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip />
                </PieChart>
              </ResponsiveContainer>
              <div className="flex flex-wrap gap-x-4 gap-y-1 mt-2 justify-center">
                {data.negotiation_outcomes.map((entry, i) => (
                  <div key={i} className="flex items-center gap-1.5 text-xs text-gray-600">
                    <span className="w-2.5 h-2.5 rounded-full shrink-0" style={{ backgroundColor: OUTCOME_COLORS[entry.name] || COLORS[i % COLORS.length] }} />
                    {entry.name} ({total > 0 ? ((entry.count/total)*100).toFixed(0) : 0}%)
                  </div>
                ))}
              </div>
            </>
          )}
        </div>

        {/* Margin Distribution: histogram showing how many deals fall into each
            profit margin bucket (e.g. "0-5%", "5-10%", etc.). */}
        <div className="bg-gray-50 rounded-lg p-4">
          <h3 className="text-sm font-semibold text-gray-700 mb-3">Margin Distribution (vs. Load Board Rate)</h3>
          {data.margin_distribution.length === 0 ? <EmptyState /> : (
            <ResponsiveContainer width="100%" height={250}>
              <BarChart data={data.margin_distribution}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                <XAxis dataKey="range" tick={{ fontSize: 12 }} stroke="#9ca3af" />
                <YAxis tick={{ fontSize: 12 }} stroke="#9ca3af" />
                <Tooltip />
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
