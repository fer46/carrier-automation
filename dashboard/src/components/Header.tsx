/**
 * Header.tsx -- Top navigation bar with branding, time range selector, and refresh control.
 *
 * The header is always visible at the top of the viewport and provides:
 *   1. App branding (logo placeholder + title)
 *   2. Time range toggle buttons (1d / 7d / 30d) that filter every analytics query
 *   3. A manual "Refresh" button
 */

export type TimeRange = '1d' | '7d' | '30d';

interface HeaderProps {
  activeRange: TimeRange;
  onRangeChange: (range: TimeRange) => void;
  onRefresh: () => void;
}

const RANGES: { value: TimeRange; label: string }[] = [
  { value: '1d', label: '1D' },
  { value: '7d', label: '7D' },
  { value: '30d', label: '30D' },
];

export default function Header({ activeRange, onRangeChange, onRefresh }: HeaderProps) {
  return (
    <header className="bg-white border-b border-gray-200 px-6 py-4 flex items-center justify-between">
      {/* Left side: app branding */}
      <div className="flex items-center gap-3">
        <div className="w-8 h-8 bg-black rounded-lg flex items-center justify-center">
          <span className="text-white font-bold text-sm">BRL</span>
        </div>
        <div>
          <h1 className="text-lg font-bold text-black leading-tight">Broker Robot Logistics</h1>
          <p className="text-[11px] text-gray-400 leading-tight">Carrier Load Analytics</p>
        </div>
      </div>

      {/* Right side: time range toggle + refresh button */}
      <div className="flex items-center gap-4">
        <div className="flex rounded-lg border border-gray-300 overflow-hidden">
          {RANGES.map(({ value, label }) => (
            <button
              key={value}
              onClick={() => onRangeChange(value)}
              className={`px-4 py-1.5 text-sm font-medium transition-colors ${
                activeRange === value
                  ? 'bg-black text-white'
                  : 'bg-white text-gray-500 hover:bg-gray-50'
              }`}
            >
              {label}
            </button>
          ))}
        </div>

        <button
          onClick={onRefresh}
          className="bg-black text-white px-3 py-1.5 rounded-md text-sm font-medium hover:bg-gray-800 transition-colors"
        >
          Refresh
        </button>
      </div>
    </header>
  );
}
