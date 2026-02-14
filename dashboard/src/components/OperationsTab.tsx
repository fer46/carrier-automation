/**
 * OperationsTab.tsx -- "Operations" tab content showing call activity metrics.
 *
 * This tab gives the operations team a bird's-eye view of carrier call activity
 * through four visualisations laid out in a 2x2 grid on large screens:
 *
 *   1. Call Volume Over Time  (AreaChart)   -- daily call count trend
 *   2. Outcome Distribution   (PieChart)    -- accepted / rejected / transferred / etc.
 *   3. Rejection Reasons      (BarChart)    -- horizontal bars for top rejection reasons
 *   4. Avg Call Duration      (LineChart)   -- daily average duration trend
 *
 * Every chart gracefully falls back to <EmptyState /> when its data array is
 * empty, preventing Recharts from rendering a broken or confusing blank chart.
 */

import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell, BarChart, Bar, LineChart, Line,
} from 'recharts';
import type { OperationsData } from '../types';
import EmptyState from './EmptyState';

// Colour palette for pie/bar slices -- cycles if there are more segments than colours.
const COLORS = ['#10b981', '#f59e0b', '#3b82f6', '#ef4444', '#8b5cf6'];

interface Props {
  data: OperationsData | null; // null while the initial fetch is still loading
}

export default function OperationsTab({ data }: Props) {
  // Show a placeholder if the parent hasn't fetched data yet.
  if (!data) return <EmptyState />;

  // Transform the outcome_distribution Record into an array format that Recharts
  // expects for PieChart data: [{ name: "accepted", value: 42 }, ...].
  const outcomeData = Object.entries(data.outcome_distribution).map(([name, value]) => ({
    name, value,
  }));

  // Pre-compute the total so each pie label can show a percentage.
  const total = outcomeData.reduce((s, d) => s + d.value, 0);

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">

      {/* ------- Chart 1: Call Volume Over Time (Area Chart) ------- */}
      <div className="bg-slate-50 rounded-lg p-4">
        <h3 className="text-sm font-semibold text-slate-700 mb-3">Call Volume Over Time</h3>
        {data.calls_over_time.length === 0 ? <EmptyState /> : (
          <ResponsiveContainer width="100%" height={250}>
            <AreaChart data={data.calls_over_time}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
              <XAxis dataKey="date" tick={{ fontSize: 12 }} stroke="#94a3b8" />
              <YAxis tick={{ fontSize: 12 }} stroke="#94a3b8" />
              <Tooltip />
              {/* Semi-transparent fill gives a subtle "area under the curve" effect. */}
              <Area type="monotone" dataKey="count" stroke="#3b82f6" fill="#3b82f6" fillOpacity={0.15} />
            </AreaChart>
          </ResponsiveContainer>
        )}
      </div>

      {/* ------- Chart 2: Outcome Distribution (Donut / Pie Chart) ------- */}
      <div className="bg-slate-50 rounded-lg p-4">
        <h3 className="text-sm font-semibold text-slate-700 mb-3">Outcome Distribution</h3>
        {outcomeData.length === 0 ? <EmptyState /> : (
          <ResponsiveContainer width="100%" height={250}>
            <PieChart>
              {/* innerRadius > 0 creates a donut shape; label renders percentage next to each slice. */}
              <Pie data={outcomeData} cx="50%" cy="50%" innerRadius={60} outerRadius={90}
                   dataKey="value" nameKey="name" label={({ name, value }) => `${name} ${total > 0 ? ((value/total)*100).toFixed(0) : 0}%`}>
                {/* Cycle through the COLORS palette for each outcome slice. */}
                {outcomeData.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
              </Pie>
              <Tooltip />
            </PieChart>
          </ResponsiveContainer>
        )}
      </div>

      {/* ------- Chart 3: Rejection Reasons (Horizontal Bar Chart) ------- */}
      <div className="bg-slate-50 rounded-lg p-4">
        <h3 className="text-sm font-semibold text-slate-700 mb-3">Rejection Reasons</h3>
        {data.rejection_reasons.length === 0 ? <EmptyState message="No rejections recorded" /> : (
          <ResponsiveContainer width="100%" height={250}>
            {/* layout="vertical" flips axes so bars grow left-to-right and
                category labels appear on the Y axis for readability. */}
            <BarChart data={data.rejection_reasons} layout="vertical">
              <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
              <XAxis type="number" tick={{ fontSize: 12 }} stroke="#94a3b8" />
              <YAxis type="category" dataKey="reason" tick={{ fontSize: 12 }} stroke="#94a3b8" width={140} />
              <Tooltip />
              {/* radius gives rounded right-side corners to match the design system. */}
              <Bar dataKey="count" fill="#f59e0b" radius={[0, 4, 4, 0]} />
            </BarChart>
          </ResponsiveContainer>
        )}
      </div>

      {/* ------- Chart 4: Average Call Duration Over Time (Line Chart) ------- */}
      <div className="bg-slate-50 rounded-lg p-4">
        <h3 className="text-sm font-semibold text-slate-700 mb-3">Avg Call Duration Over Time</h3>
        {data.avg_duration_over_time.length === 0 ? <EmptyState /> : (
          <ResponsiveContainer width="100%" height={250}>
            <LineChart data={data.avg_duration_over_time}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
              <XAxis dataKey="date" tick={{ fontSize: 12 }} stroke="#94a3b8" />
              <YAxis tick={{ fontSize: 12 }} stroke="#94a3b8" />
              {/* Custom formatter converts raw seconds into a friendlier "X.X min" string.
                  Recharts types `value` as `number | undefined`, so we default to 0. */}
              <Tooltip formatter={(v: number | undefined) => `${((v ?? 0) / 60).toFixed(1)} min`} />
              <Line type="monotone" dataKey="avg_duration" stroke="#8b5cf6" strokeWidth={2} dot={false} />
            </LineChart>
          </ResponsiveContainer>
        )}
      </div>
    </div>
  );
}
