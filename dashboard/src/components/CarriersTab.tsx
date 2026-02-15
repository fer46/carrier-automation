/**
 * CarriersTab.tsx -- "Carriers" tab content showing carrier behaviour and engagement metrics.
 *
 * This tab provides insights into the carrier side of the conversation:
 *
 *   Section 1 (2x2 chart grid):
 *     - Sentiment Over Time       (stacked AreaChart) -- daily breakdown of
 *       positive / neutral / negative carrier sentiment
 *     - Engagement Levels         (donut PieChart) -- e.g. "high", "medium", "low"
 *     - Top Carrier Objections    (horizontal BarChart) -- most common push-backs
 *     - Top Carrier Questions     (horizontal BarChart) -- most frequent questions
 *
 *   Section 2 (1+2 column grid):
 *     - Future Interest Rate      (single big number) -- percentage of carriers who
 *       expressed willingness to work with us again
 *     - Carrier Leaderboard       (table spanning 2 cols) -- top carriers ranked by
 *       acceptance rate with a visual progress bar
 */

import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell, BarChart, Bar, Legend,
} from 'recharts';
import type { CarriersData } from '../types';
import EmptyState from './EmptyState';

// Engagement level pie chart colours: blue (high), amber (medium), grey (low).
const ENG_COLORS = ['#3b82f6', '#f59e0b', '#94a3b8'];

interface Props {
  data: CarriersData | null; // null while the initial fetch is still loading
}

export default function CarriersTab({ data }: Props) {
  if (!data) return <EmptyState />;

  // Transform engagement_levels Record into the array format Recharts needs.
  const engData = Object.entries(data.engagement_levels).map(([name, value]) => ({ name, value }));

  return (
    <div className="space-y-6">

      {/* ------- Section 1: 2x2 Chart Grid ------- */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">

        {/* Sentiment Over Time: stacked area chart showing how carrier sentiment
            (positive / neutral / negative) trends over the selected date range. */}
        <div className="bg-slate-50 rounded-lg p-4">
          <h3 className="text-sm font-semibold text-slate-700 mb-3">Sentiment Over Time</h3>
          {data.sentiment_over_time.length === 0 ? <EmptyState /> : (
            <ResponsiveContainer width="100%" height={250}>
              <AreaChart data={data.sentiment_over_time}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                <XAxis dataKey="date" tick={{ fontSize: 12 }} stroke="#94a3b8" />
                <YAxis tick={{ fontSize: 12 }} stroke="#94a3b8" />
                <Tooltip />
                <Legend />
                {/* stackId="1" ensures all three areas stack on top of each other
                    rather than overlapping, giving a clear 100% stacked view. */}
                <Area type="monotone" dataKey="positive" stackId="1" stroke="#10b981" fill="#10b981" fillOpacity={0.6} />
                <Area type="monotone" dataKey="neutral" stackId="1" stroke="#94a3b8" fill="#94a3b8" fillOpacity={0.6} />
                <Area type="monotone" dataKey="negative" stackId="1" stroke="#ef4444" fill="#ef4444" fillOpacity={0.6} />
              </AreaChart>
            </ResponsiveContainer>
          )}
        </div>

        {/* Engagement Levels: donut chart showing the proportion of carriers at
            each engagement level (e.g. high / medium / low). */}
        <div className="bg-slate-50 rounded-lg p-4">
          <h3 className="text-sm font-semibold text-slate-700 mb-3">Engagement Levels</h3>
          {engData.length === 0 ? <EmptyState /> : (
            <ResponsiveContainer width="100%" height={250}>
              <PieChart>
                <Pie data={engData} cx="50%" cy="50%" innerRadius={60} outerRadius={90}
                     dataKey="value" nameKey="name"
                     label={({ name, value }) => `${name} (${value})`}>
                  {engData.map((_, i) => <Cell key={i} fill={ENG_COLORS[i % ENG_COLORS.length]} />)}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          )}
        </div>

        {/* Top Carrier Objections: horizontal bar chart ranking the most frequent
            reasons carriers push back (e.g. "Rate too low", "Wrong lane"). */}
        <div className="bg-slate-50 rounded-lg p-4">
          <h3 className="text-sm font-semibold text-slate-700 mb-3">Top Carrier Objections</h3>
          {data.top_objections.length === 0 ? <EmptyState message="No objections recorded" /> : (
            <ResponsiveContainer width="100%" height={250}>
              <BarChart data={data.top_objections} layout="vertical">
                <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                <XAxis type="number" tick={{ fontSize: 12 }} stroke="#94a3b8" />
                <YAxis type="category" dataKey="objection" tick={{ fontSize: 12 }} stroke="#94a3b8" width={150} />
                <Tooltip />
                <Bar dataKey="count" fill="#f59e0b" radius={[0, 4, 4, 0]} />
              </BarChart>
            </ResponsiveContainer>
          )}
        </div>


      </div>

      {/* ------- Lane Intelligence Section ------- */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">

        {/* Top Requested Lanes */}
        <div className="bg-slate-50 rounded-lg p-4">
          <h3 className="text-sm font-semibold text-slate-700 mb-3">Top Requested Lanes</h3>
          {data.top_requested_lanes.length === 0 ? <EmptyState message="No lane data yet" /> : (
            <div className="space-y-2">
              {data.top_requested_lanes.map((lane, i) => (
                <div key={i} className="flex items-center justify-between text-sm">
                  <span className="text-slate-700 truncate mr-2">{lane.lane}</span>
                  <span className="text-slate-500 font-medium shrink-0">{lane.count}</span>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Top Actual Lanes */}
        <div className="bg-slate-50 rounded-lg p-4">
          <h3 className="text-sm font-semibold text-slate-700 mb-3">Top Actual Lanes</h3>
          {data.top_actual_lanes.length === 0 ? <EmptyState message="No lane data yet" /> : (
            <div className="space-y-2">
              {data.top_actual_lanes.map((lane, i) => (
                <div key={i} className="flex items-center justify-between text-sm">
                  <span className="text-slate-700 truncate mr-2">{lane.lane}</span>
                  <span className="text-slate-500 font-medium shrink-0">{lane.count}</span>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Equipment Types */}
        <div className="bg-slate-50 rounded-lg p-4">
          <h3 className="text-sm font-semibold text-slate-700 mb-3">Equipment Types</h3>
          {data.equipment_distribution.length === 0 ? <EmptyState message="No equipment data yet" /> : (
            <ResponsiveContainer width="100%" height={200}>
              <PieChart>
                <Pie
                  data={data.equipment_distribution.map((e) => ({ name: e.equipment_type, value: e.count }))}
                  cx="50%" cy="50%" innerRadius={40} outerRadius={70}
                  dataKey="value" nameKey="name"
                  label={({ name, value }) => `${name} (${value})`}
                >
                  {data.equipment_distribution.map((_, i) => (
                    <Cell key={i} fill={ENG_COLORS[i % ENG_COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          )}
        </div>
      </div>

      {/* ------- Section 2: Future Interest Rate + Carrier Leaderboard ------- */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">

        {/* Future Interest Rate: a single headline metric showing what percentage
            of carriers expressed willingness to accept loads in the future. */}
        <div className="bg-slate-50 rounded-lg p-4 text-center flex flex-col items-center justify-center">
          <p className="text-sm text-slate-500 mb-2">Future Interest Rate</p>
          <p className="text-4xl font-bold text-blue-600">{data.future_interest_rate}%</p>
          <p className="text-xs text-slate-400 mt-1">Carriers expressing future interest</p>
        </div>

        {/* Carrier Leaderboard: sortable table of top-performing carriers.
            Spans 2 columns on large screens to give the table breathing room. */}
        <div className="bg-slate-50 rounded-lg p-4 lg:col-span-2">
          <h3 className="text-sm font-semibold text-slate-700 mb-3">Carrier Leaderboard</h3>
          {data.carrier_leaderboard.length === 0 ? <EmptyState /> : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left text-slate-500 border-b border-slate-200">
                    <th className="pb-2 font-medium">Carrier</th>
                    <th className="pb-2 font-medium">MC#</th>
                    <th className="pb-2 font-medium">Calls</th>
                    <th className="pb-2 font-medium">Accept Rate</th>
                  </tr>
                </thead>
                <tbody>
                  {data.carrier_leaderboard.map((row) => (
                    <tr key={row.mc_number} className="border-b border-slate-100">
                      <td className="py-2 font-medium text-slate-700">{row.carrier_name}</td>
                      <td className="py-2 text-slate-500">{row.mc_number}</td>
                      <td className="py-2 text-slate-600">{row.calls}</td>
                      <td className="py-2">
                        {/* Visual progress bar + numeric label for acceptance rate.
                            Capped at 100% width to prevent overflow on bad data. */}
                        <div className="flex items-center gap-2">
                          <div className="w-24 bg-slate-200 rounded-full h-2">
                            <div
                              className="bg-emerald-500 h-2 rounded-full"
                              style={{ width: `${Math.min(row.acceptance_rate, 100)}%` }}
                            />
                          </div>
                          <span className="text-slate-600">{row.acceptance_rate}%</span>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
