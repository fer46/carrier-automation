/**
 * OperationsTab.tsx -- "Operations" tab content showing call activity metrics.
 *
 * This tab gives the operations team a bird's-eye view of carrier call activity:
 *
 *   1. Conversion Funnel (full-width horizontal bar chart):
 *      - Shows where the AI loses carriers through the pipeline stages
 *
 *   2. Charts (2-column grid):
 *      - Call Volume Over Time  (AreaChart)  -- daily call count trend
 *      - Rejection Reasons      (BarChart)   -- horizontal bars for top rejection reasons
 *
 * Every chart gracefully falls back to <EmptyState /> when its data array is
 * empty, preventing Recharts from rendering a broken or confusing blank chart.
 */

import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  BarChart, Bar, Cell,
} from 'recharts';
import type { OperationsData } from '../types';
import EmptyState from './EmptyState';

interface Props {
  data: OperationsData | null; // null while the initial fetch is still loading
}

export default function OperationsTab({ data }: Props) {
  // Show a placeholder if the parent hasn't fetched data yet.
  if (!data) return <EmptyState />;

  // Map internal stage names to human-readable labels for the funnel chart.
  const stageLabels: Record<string, string> = {
    call_started: 'Call Started',
    fmcsa_verified: 'FMCSA Verified',
    load_matched: 'Load Matched',
    offer_pitched: 'Offer Pitched',
    negotiation_entered: 'Negotiation Entered',
    deal_agreed: 'Deal Agreed',
    transferred_to_sales: 'Transferred to Sales',
  };

  const funnelData = data.funnel.map((s) => ({
    ...s,
    label: stageLabels[s.stage] || s.stage,
  }));

  return (
    <div className="space-y-6">

      {/* ------- Conversion Funnel (full-width horizontal bar chart) ------- */}
      <div className="bg-gray-50 rounded-lg p-4">
        <h3 className="text-sm font-semibold text-gray-700 mb-3">Conversion Funnel</h3>
        {funnelData.length === 0 || funnelData[0].count === 0 ? <EmptyState message="No funnel data yet" /> : (
          <ResponsiveContainer width="100%" height={280}>
            <BarChart data={funnelData} layout="vertical">
              <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
              <XAxis type="number" tick={{ fontSize: 12 }} stroke="#9ca3af" />
              <YAxis type="category" dataKey="label" tick={{ fontSize: 12 }} stroke="#9ca3af" width={160} />
              <Tooltip
                formatter={(v: number | undefined) => `${(v ?? 0).toLocaleString()}`}
                labelFormatter={(label) => {
                  const stage = funnelData.find((s) => s.label === String(label));
                  return stage ? `${label} (${stage.drop_off_percent}% drop-off)` : String(label);
                }}
              />
              <Bar dataKey="count" radius={[0, 4, 4, 0]}>
                {funnelData.map((_, i) => (
                  <Cell
                    key={i}
                    fill={i === funnelData.length - 1 ? '#22c55e' : '#3b82f6'}
                  />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        )}
      </div>

      {/* ------- Charts (2-column grid) ------- */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">

        {/* Call Volume Over Time (Area Chart) */}
        <div className="bg-gray-50 rounded-lg p-4">
          <h3 className="text-sm font-semibold text-gray-700 mb-3">Call Volume Over Time</h3>
          {data.calls_over_time.length === 0 ? <EmptyState /> : (
            <ResponsiveContainer width="100%" height={250}>
              <AreaChart data={data.calls_over_time}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                <XAxis dataKey="date" tick={{ fontSize: 12 }} stroke="#9ca3af" />
                <YAxis tick={{ fontSize: 12 }} stroke="#9ca3af" />
                <Tooltip />
                <Area type="monotone" dataKey="count" stroke="#3b82f6" fill="#3b82f6" fillOpacity={0.15} />
              </AreaChart>
            </ResponsiveContainer>
          )}
        </div>

        {/* Rejection Reasons (Horizontal Bar Chart) */}
        <div className="bg-gray-50 rounded-lg p-4">
          <h3 className="text-sm font-semibold text-gray-700 mb-3">Rejection Reasons</h3>
          {data.rejection_reasons.length === 0 ? <EmptyState message="No rejections recorded" /> : (
            <ResponsiveContainer width="100%" height={250}>
              <BarChart data={data.rejection_reasons} layout="vertical">
                <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                <XAxis type="number" tick={{ fontSize: 12 }} stroke="#9ca3af" />
                <YAxis type="category" dataKey="reason" tick={{ fontSize: 12 }} stroke="#9ca3af" width={140} />
                <Tooltip />
                <Bar dataKey="count" fill="#f97316" radius={[0, 4, 4, 0]} />
              </BarChart>
            </ResponsiveContainer>
          )}
        </div>
      </div>

    </div>
  );
}
