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
  format?: 'number' | 'percent' | 'duration' | 'dollar';
  color?: 'default' | 'green';
  tooltip?: string;
}

const colorMap = {
  default: 'bg-white border-gray-200 text-black',
  green: 'bg-emerald-50 border-emerald-200 text-emerald-700',
};

/**
 * Converts a raw numeric value into a display-friendly string based on the
 * requested format.  String values pass through unchanged (useful when the
 * caller has already formatted the value).
 */
function formatValue(value: string | number, format?: string): string {
  if (typeof value === 'string') return value;
  // Dollar: locale-formatted with "$" prefix.
  if (format === 'dollar') return `$${value.toLocaleString(undefined, { minimumFractionDigits: 0, maximumFractionDigits: 2 })}`;
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

export default function KPICard({ label, value, format, color = 'default', tooltip }: KPICardProps) {
  return (
    <div className={`rounded-xl border p-5 ${colorMap[color]}`}>
      {tooltip ? (
        <p className="text-sm font-medium opacity-70 mb-1 relative group cursor-help">
          {label}
          <span className="invisible group-hover:visible absolute left-0 top-full mt-1 z-10 w-56 rounded-lg bg-gray-800 text-white text-xs font-normal p-2.5 leading-relaxed shadow-lg">
            {tooltip}
          </span>
        </p>
      ) : (
        <p className="text-sm font-medium opacity-70 mb-1">{label}</p>
      )}
      <p className="text-3xl font-bold tracking-tight">{formatValue(value, format)}</p>
    </div>
  );
}
