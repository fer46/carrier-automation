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
const COLORS = ['#ef4444', '#f59e0b', '#10b981', '#3b82f6', '#8b5cf6'];

// Semantic colours for the negotiation outcomes donut chart.
const OUTCOME_COLORS: Record<string, string> = {
  'Accepted at First Offer': '#10b981',  // emerald
  'Negotiated & Agreed': '#3b82f6',       // blue
  'No Deal': '#ef4444',                   // red
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
        <div className="bg-slate-50 rounded-lg p-4 text-center">
          <p className="text-sm text-slate-500">Avg Savings / Deal</p>
          <p className="text-2xl font-bold text-emerald-600">${data.avg_savings.toLocaleString()}</p>
        </div>
        <div className="bg-slate-50 rounded-lg p-4 text-center">
          <p className="text-sm text-slate-500">Avg Savings %</p>
          <p className="text-2xl font-bold text-emerald-600">{data.avg_savings_percent}%</p>
        </div>
        <div className="bg-slate-50 rounded-lg p-4 text-center">
          <p className="text-sm text-slate-500">Avg Rounds</p>
          <p className="text-2xl font-bold text-slate-800">{data.avg_rounds}</p>
        </div>
      </div>

      {/* ------- Section 2: Charts (Rate Progression + Margin Distribution) ------- */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">

        {/* Negotiation Outcomes: donut chart showing what happens when the AI
            talks to carriers — accepted at first offer, negotiated, or no deal. */}
        <div className="bg-slate-50 rounded-lg p-4">
          <h3 className="text-sm font-semibold text-slate-700 mb-3">Negotiation Outcomes</h3>
          {total === 0 ? <EmptyState /> : (
            <ResponsiveContainer width="100%" height={250}>
              <PieChart>
                <Pie data={data.negotiation_outcomes} cx="50%" cy="50%" innerRadius={60} outerRadius={90}
                     dataKey="count" nameKey="name"
                     label={({ name, count }: { name: string; count: number }) => `${name} ${total > 0 ? ((count/total)*100).toFixed(0) : 0}%`}>
                  {data.negotiation_outcomes.map((entry, i) => (
                    <Cell key={i} fill={OUTCOME_COLORS[entry.name] || COLORS[i % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip />
              </PieChart>
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
