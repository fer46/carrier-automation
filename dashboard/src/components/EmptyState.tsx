/**
 * EmptyState.tsx -- Fallback placeholder shown when a chart or section has no data.
 *
 * Used throughout every tab component as a graceful "no data" indicator instead
 * of rendering an empty or broken chart.  Accepts an optional custom message so
 * each chart can explain *why* there is nothing to show (e.g. "No rejections
 * recorded" vs. the generic "No data available").
 */

export default function EmptyState({ message }: { message?: string }) {
  return (
    <div className="text-center py-12 text-gray-400">
      <p>{message || 'No data available'}</p>
    </div>
  );
}
