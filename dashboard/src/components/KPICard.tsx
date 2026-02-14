/**
 * KPICard.tsx -- A single key-performance-indicator card used in the hero row.
 *
 * The hero row at the top of the dashboard renders 7 of these cards to give an
 * at-a-glance view of the most important metrics.  Each card supports:
 *   - A human-readable label (e.g. "Total Calls")
 *   - A numeric or string value
 *   - An optional format hint so the value is displayed correctly:
 *       'percent'  -> "72.3%"
 *       'duration' -> "4m 32s" (assumes value is in seconds)
 *       'number'   -> locale-formatted integer (e.g. "1,234")
 *   - A semantic color that tints the card background and text
 */

interface KPICardProps {
  label: string;
  value: string | number;
  format?: 'number' | 'percent' | 'duration';
  color?: 'green' | 'amber' | 'blue' | 'slate';
}

/**
 * Maps each semantic color name to a set of Tailwind utility classes that
 * style the card's background, border, and text colour.
 */
const colorMap = {
  green: 'bg-emerald-50 border-emerald-200 text-emerald-700',
  amber: 'bg-amber-50 border-amber-200 text-amber-700',
  blue: 'bg-blue-50 border-blue-200 text-blue-700',
  slate: 'bg-slate-50 border-slate-200 text-slate-700',
};

/**
 * Converts a raw numeric value into a display-friendly string based on the
 * requested format.  String values pass through unchanged (useful when the
 * caller has already formatted the value).
 */
function formatValue(value: string | number, format?: string): string {
  if (typeof value === 'string') return value;
  // Percentage: one decimal place with a "%" suffix.
  if (format === 'percent') return `${value.toFixed(1)}%`;
  // Duration: convert seconds into "Xm Ys" (minutes and seconds).
  if (format === 'duration') {
    const mins = Math.floor(value / 60);
    const secs = Math.round(value % 60);
    return `${mins}m ${secs}s`;
  }
  // Integers get locale-formatted thousands separators (e.g. 1,234).
  if (Number.isInteger(value)) return value.toLocaleString();
  // Fallback for floats without a specific format: one decimal place.
  return value.toFixed(1);
}

export default function KPICard({ label, value, format, color = 'slate' }: KPICardProps) {
  return (
    <div className={`rounded-xl border p-5 ${colorMap[color]}`}>
      {/* Label is rendered at reduced opacity so the bold value stands out. */}
      <p className="text-sm font-medium opacity-70 mb-1">{label}</p>
      <p className="text-3xl font-bold tracking-tight">{formatValue(value, format)}</p>
    </div>
  );
}
