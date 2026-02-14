/**
 * AIQualityTab.tsx -- "AI Quality" tab content showing AI performance metrics.
 *
 * This tab helps the team monitor how well the AI agent performs during carrier
 * calls.  It is structured in two main sections:
 *
 *   1. Summary stat cards (4-column row):
 *      - Protocol Compliance  -- green if >= 90%, amber otherwise
 *      - Avg Interruptions    -- how often carriers interrupt the AI
 *      - Transcription Errors -- green if <= 5%, red otherwise
 *      - Carrier Repeat Rate  -- green if <= 10% (low repeat = good coverage)
 *
 *   2. Charts (2-column grid, 3 charts total):
 *      - Common Protocol Violations (horizontal BarChart)
 *      - Interruptions Over Time    (LineChart trend)
 *      - Tone Quality Distribution  (donut PieChart)
 *
 * Colour thresholds are intentionally hardcoded here rather than configurable
 * because they represent industry/team standards that rarely change.
 */

import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  BarChart, Bar, PieChart, Pie, Cell,
} from 'recharts';
import type { AIQualityData } from '../types';
import EmptyState from './EmptyState';

// Tone pie chart colours: green for positive, grey for neutral, red for negative.
const COLORS = ['#10b981', '#94a3b8', '#ef4444'];

interface Props {
  data: AIQualityData | null; // null while the initial fetch is still loading
}

export default function AIQualityTab({ data }: Props) {
  if (!data) return <EmptyState />;

  // Transform the tone_quality_distribution Record into the array format that
  // Recharts PieChart expects: [{ name: "professional", value: 80 }, ...].
  const toneData = Object.entries(data.tone_quality_distribution).map(([name, value]) => ({
    name, value,
  }));

  return (
    <div className="space-y-6">

      {/* ------- Section 1: AI Quality KPI Cards (4-column row) ------- */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">

        {/* Protocol Compliance: the most important AI quality metric.
            Green (>= 90%) means the AI reliably follows the call script. */}
        <div className="bg-slate-50 rounded-lg p-4 text-center">
          <p className="text-sm text-slate-500">Protocol Compliance</p>
          <p className={`text-3xl font-bold ${data.protocol_compliance_rate >= 90 ? 'text-emerald-600' : 'text-amber-600'}`}>
            {data.protocol_compliance_rate}%
          </p>
        </div>

        {/* Average interruptions per call (lower is better). */}
        <div className="bg-slate-50 rounded-lg p-4 text-center">
          <p className="text-sm text-slate-500">Avg Interruptions</p>
          <p className="text-3xl font-bold text-slate-800">{data.avg_interruptions}</p>
        </div>

        {/* Transcription error rate: green (<= 5%) means the speech-to-text
            pipeline is accurate enough for reliable analysis. */}
        <div className="bg-slate-50 rounded-lg p-4 text-center">
          <p className="text-sm text-slate-500">Transcription Errors</p>
          <p className={`text-3xl font-bold ${data.transcription_error_rate <= 5 ? 'text-emerald-600' : 'text-red-500'}`}>
            {data.transcription_error_rate}%
          </p>
        </div>

        {/* Carrier repeat rate: percentage of carriers who had to be called
            again.  Low (<= 10%) is green -- most issues resolved in one call. */}
        <div className="bg-slate-50 rounded-lg p-4 text-center">
          <p className="text-sm text-slate-500">Carrier Repeat Rate</p>
          <p className={`text-3xl font-bold ${data.carrier_repeat_rate <= 10 ? 'text-emerald-600' : 'text-amber-600'}`}>
            {data.carrier_repeat_rate}%
          </p>
        </div>
      </div>

      {/* ------- Section 2: Charts ------- */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">

        {/* Common Protocol Violations: horizontal bar chart ranking the most
            frequent ways the AI deviated from the expected call protocol. */}
        <div className="bg-slate-50 rounded-lg p-4">
          <h3 className="text-sm font-semibold text-slate-700 mb-3">Common Protocol Violations</h3>
          {data.common_violations.length === 0 ? <EmptyState message="No violations recorded" /> : (
            <ResponsiveContainer width="100%" height={250}>
              <BarChart data={data.common_violations} layout="vertical">
                <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                <XAxis type="number" tick={{ fontSize: 12 }} stroke="#94a3b8" />
                <YAxis type="category" dataKey="violation" tick={{ fontSize: 12 }} stroke="#94a3b8" width={150} />
                <Tooltip />
                {/* Red bars emphasise that violations are negative events. */}
                <Bar dataKey="count" fill="#ef4444" radius={[0, 4, 4, 0]} />
              </BarChart>
            </ResponsiveContainer>
          )}
        </div>

        {/* Interruptions Over Time: line chart tracking the daily average number
            of interruptions per call -- useful for spotting regression trends. */}
        <div className="bg-slate-50 rounded-lg p-4">
          <h3 className="text-sm font-semibold text-slate-700 mb-3">Interruptions Over Time</h3>
          {data.interruptions_over_time.length === 0 ? <EmptyState /> : (
            <ResponsiveContainer width="100%" height={250}>
              <LineChart data={data.interruptions_over_time}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                <XAxis dataKey="date" tick={{ fontSize: 12 }} stroke="#94a3b8" />
                <YAxis tick={{ fontSize: 12 }} stroke="#94a3b8" />
                <Tooltip />
                <Line type="monotone" dataKey="avg" stroke="#f59e0b" strokeWidth={2} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          )}
        </div>

        {/* Tone Quality Distribution: donut chart showing the breakdown of
            AI tone assessments (e.g. "professional", "neutral", "aggressive"). */}
        <div className="bg-slate-50 rounded-lg p-4">
          <h3 className="text-sm font-semibold text-slate-700 mb-3">Tone Quality Distribution</h3>
          {toneData.length === 0 ? <EmptyState /> : (
            <ResponsiveContainer width="100%" height={250}>
              <PieChart>
                <Pie data={toneData} cx="50%" cy="50%" innerRadius={60} outerRadius={90}
                     dataKey="value" nameKey="name"
                     label={({ name, value }) => `${name} (${value})`}>
                  {toneData.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          )}
        </div>
      </div>
    </div>
  );
}
