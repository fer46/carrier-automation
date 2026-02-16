/**
 * CarriersTab.tsx -- "Carriers" tab content showing carrier intelligence metrics.
 *
 * This tab provides actionable insights into carrier behaviour and market patterns:
 *
 *   Section 1 (3-column grid -- Lane Intelligence):
 *     - Top Requested Lanes    (ranked list) -- lanes carriers ask about most
 *     - Top Actual Lanes       (ranked list) -- lanes where deals actually happen
 *     - Equipment Types        (donut PieChart) -- fleet mix across conversations
 *
 *   Section 2 (2-column grid):
 *     - Top Carrier Objections (horizontal BarChart) -- most common push-backs
 *     - Carrier Leaderboard    (table) -- top carriers by acceptance rate
 */

import {
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell, BarChart, Bar,
} from 'recharts';
import type { CarriersData } from '../types';
import EmptyState from './EmptyState';

// Equipment donut chart colours.
const EQUIP_COLORS = ['#3b82f6', '#f59e0b', '#10b981', '#ef4444', '#8b5cf6'];

interface Props {
  data: CarriersData | null; // null while the initial fetch is still loading
}

export default function CarriersTab({ data }: Props) {
  if (!data) return <EmptyState />;

  return (
    <div className="space-y-6">

      {/* ------- Section 1: Lane Intelligence (3-column grid) ------- */}
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
                    <Cell key={i} fill={EQUIP_COLORS[i % EQUIP_COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          )}
        </div>
      </div>

      {/* ------- Section 2: Objections + Carrier Leaderboard (2-column grid) ------- */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">

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

        {/* Carrier Leaderboard: table of top-performing carriers ranked by volume. */}
        <div className="bg-slate-50 rounded-lg p-4">
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
