/**
 * Header.tsx -- Top navigation bar with branding, date range picker, and refresh control.
 *
 * The header is always visible at the top of the viewport and provides:
 *   1. App branding (logo placeholder + title)
 *   2. Date range inputs ("From" / "To") that filter every analytics query
 *   3. A manual "Refresh" button with a live countdown showing seconds until
 *      the next automatic poll (the App component auto-refreshes every 30s)
 *
 * This is a controlled component -- all state lives in the parent App and is
 * passed down via props.  Date changes trigger an immediate re-fetch in App
 * because `fetchAll` depends on `dateFrom` / `dateTo`.
 */

interface HeaderProps {
  dateFrom: string;                           // Current "from" date (ISO string or empty)
  dateTo: string;                             // Current "to" date (ISO string or empty)
  onDateChange: (from: string, to: string) => void; // Called when either date input changes
  onRefresh: () => void;                      // Called when the user clicks Refresh
  countdown: number;                          // Seconds remaining until next auto-refresh
}

export default function Header({ dateFrom, dateTo, onDateChange, onRefresh, countdown }: HeaderProps) {
  return (
    <header className="bg-white border-b border-slate-200 px-6 py-4 flex items-center justify-between">
      {/* Left side: app branding */}
      <div className="flex items-center gap-3">
        {/* Blue square with "CL" initials serves as a lightweight logo placeholder. */}
        <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center">
          <span className="text-white font-bold text-sm">CL</span>
        </div>
        <h1 className="text-xl font-bold text-slate-800">Carrier Load Analytics</h1>
      </div>

      {/* Right side: date range picker + refresh button */}
      <div className="flex items-center gap-4">
        {/* Date range inputs -- when left empty, the backend returns the full range. */}
        <div className="flex items-center gap-2 text-sm">
          <label className="text-slate-500">From</label>
          <input
            type="date"
            value={dateFrom}
            onChange={(e) => onDateChange(e.target.value, dateTo)}
            className="border border-slate-300 rounded-md px-2 py-1 text-sm"
          />
          <label className="text-slate-500">To</label>
          <input
            type="date"
            value={dateTo}
            onChange={(e) => onDateChange(dateFrom, e.target.value)}
            className="border border-slate-300 rounded-md px-2 py-1 text-sm"
          />
        </div>

        {/* Manual refresh button.  The countdown badge shows seconds until the
            next automatic poll so the user knows fresh data is always on its way. */}
        <button
          onClick={onRefresh}
          className="flex items-center gap-2 bg-blue-600 text-white px-3 py-1.5 rounded-md text-sm font-medium hover:bg-blue-700 transition-colors"
        >
          Refresh
          <span className="text-blue-200 text-xs">({countdown}s)</span>
        </button>
      </div>
    </header>
  );
}
