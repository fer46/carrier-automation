/**
 * GeographyTab.tsx -- "Geography" tab: US arc map of requested vs booked lanes.
 *
 * Layout: full-width centered map on top, collapsible stats panels below.
 */

import { useState, useMemo } from 'react';
import {
  ComposableMap,
  Geographies,
  Geography,
  Line,
  Marker,
} from 'react-simple-maps';
import type { GeographyData, GeoArc } from '../types';
import EmptyState from './EmptyState';

const GEO_URL = 'https://cdn.jsdelivr.net/npm/us-atlas@3/states-10m.json';

interface Props {
  data: GeographyData | null;
}

// ---------------------------------------------------------------------------
// Curved arc helpers
// ---------------------------------------------------------------------------

function curveCoords(
  fromLng: number,
  fromLat: number,
  toLng: number,
  toLat: number,
  curveFactor: number,
): [number, number][] {
  const N = 20;
  const midLng = (fromLng + toLng) / 2;
  const midLat = (fromLat + toLat) / 2;
  const dLng = Math.abs(toLng - fromLng);
  const dLat = Math.abs(toLat - fromLat);
  const dist = Math.sqrt(dLng * dLng + dLat * dLat);
  const ctrlLng = midLng;
  const ctrlLat = midLat + Math.max(dist * curveFactor, 1.2);

  const pts: [number, number][] = [];
  for (let i = 0; i <= N; i++) {
    const t = i / N;
    const u = 1 - t;
    pts.push([
      u * u * fromLng + 2 * u * t * ctrlLng + t * t * toLng,
      u * u * fromLat + 2 * u * t * ctrlLat + t * t * toLat,
    ]);
  }
  return pts;
}

// ---------------------------------------------------------------------------
// Disclosure (collapsible section)
// ---------------------------------------------------------------------------

function Disclosure({
  title,
  count,
  children,
}: {
  title: string;
  count: number;
  children: React.ReactNode;
}) {
  const [open, setOpen] = useState(false);
  return (
    <div className="border border-gray-200 rounded-lg overflow-hidden">
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center justify-between px-4 py-2.5 text-left hover:bg-gray-50 transition-colors"
      >
        <span className="text-sm font-medium text-gray-700">{title}</span>
        <div className="flex items-center gap-2">
          <span className="text-xs text-gray-400 tabular-nums">{count}</span>
          <svg
            width="16"
            height="16"
            viewBox="0 0 16 16"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.5"
            strokeLinecap="round"
            className={`text-gray-400 transition-transform ${open ? 'rotate-180' : ''}`}
          >
            <path d="M4 6l4 4 4-4" />
          </svg>
        </div>
      </button>
      {open && (
        <div className="px-4 pb-3 border-t border-gray-100">
          {children}
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Lane list row
// ---------------------------------------------------------------------------

function LaneRow({ arc, maxCount, color }: { arc: GeoArc; maxCount: number; color: 'orange' | 'green' }) {
  const barBg = color === 'orange' ? 'bg-orange-50' : 'bg-emerald-50';
  const barFill = color === 'orange' ? 'bg-orange-300' : 'bg-emerald-400';
  const countColor = color === 'orange' ? 'text-orange-400' : 'text-emerald-500';
  return (
    <div className="py-1.5">
      <div className="flex items-center justify-between text-sm">
        <span className="text-gray-600 truncate">
          {arc.origin.split(',')[0]} &rarr; {arc.destination.split(',')[0]}
        </span>
        <span className={`${countColor} tabular-nums ml-2 shrink-0 text-xs`}>
          {arc.count}
        </span>
      </div>
      <div className={`h-1 ${barBg} rounded-full mt-1`}>
        <div
          className={`h-1 ${barFill} rounded-full`}
          style={{ width: `${(arc.count / maxCount) * 100}%` }}
        />
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function GeographyTab({ data }: Props) {
  const [tooltip, setTooltip] = useState<{
    name: string;
    volume: number;
    x: number;
    y: number;
  } | null>(null);

  const overlapKeys = useMemo(() => {
    if (!data) return new Set<string>();
    const requested = new Set<string>();
    const booked = new Set<string>();
    for (const arc of data.arcs) {
      const key = `${arc.origin}|${arc.destination}`;
      if (arc.arc_type === 'requested') requested.add(key);
      else booked.add(key);
    }
    const overlaps = new Set<string>();
    for (const key of requested) {
      if (booked.has(key)) overlaps.add(key);
    }
    return overlaps;
  }, [data]);

  const radiusScale = useMemo(() => {
    if (!data || data.cities.length === 0) return () => 4;
    const vols = data.cities.map((c) => c.volume);
    const min = Math.min(...vols);
    const max = Math.max(...vols);
    const range = max - min || 1;
    return (v: number) => 3 + ((v - min) / range) * 7;
  }, [data]);

  const labeledCities = useMemo(() => {
    if (!data) return new Set<string>();
    const sorted = [...data.cities].sort((a, b) => b.volume - a.volume);
    return new Set(sorted.slice(0, 5).map((c) => c.name));
  }, [data]);

  if (!data) return <EmptyState />;
  if (data.arcs.length === 0 && data.cities.length === 0) {
    return <EmptyState message="No lane data available for the selected period" />;
  }

  const requestedArcs = data.arcs.filter((a) => a.arc_type === 'requested');
  const bookedArcs = data.arcs.filter((a) => a.arc_type === 'booked');
  const sortedCities = [...data.cities].sort((a, b) => b.volume - a.volume);

  return (
    <div>
      {/* ─── Legend ─── */}
      <div className="flex items-center gap-5 mb-3">
        <div className="flex items-center gap-1.5">
          <svg width="22" height="6" className="shrink-0">
            <path d="M0 3 Q11 0 22 3" stroke="#f97316" strokeWidth="1.5" fill="none" strokeDasharray="3 2" opacity="0.7" />
          </svg>
          <span className="text-xs text-gray-400">Requested Lanes</span>
        </div>
        <div className="flex items-center gap-1.5">
          <svg width="22" height="6" className="shrink-0">
            <path d="M0 3 Q11 0 22 3" stroke="#22c55e" strokeWidth="1.5" fill="none" />
          </svg>
          <span className="text-xs text-gray-400">Booked Lanes</span>
        </div>
        <div className="flex items-center gap-1.5 ml-auto">
          <span className="inline-block w-2 h-2 rounded-full bg-blue-500/70" />
          <span className="text-xs text-gray-400">City (sized by volume)</span>
        </div>
      </div>

      {/* ─── Full-width centered map ─── */}
      <div className="border border-gray-200 rounded-lg overflow-hidden bg-gray-50">
        <ComposableMap
          projection="geoAlbersUsa"
          projectionConfig={{ scale: 1100 }}
          width={900}
          height={540}
          style={{ width: '100%', height: 'auto' }}
        >
          <Geographies geography={GEO_URL}>
            {({ geographies }) =>
              geographies.map((geo) => (
                <Geography
                  key={geo.rsmKey}
                  geography={geo}
                  fill="#f3f4f6"
                  stroke="#d1d5db"
                  strokeWidth={0.5}
                  style={{
                    default: { outline: 'none' },
                    hover: { outline: 'none' },
                    pressed: { outline: 'none' },
                  }}
                />
              ))
            }
          </Geographies>

          {requestedArcs.map((arc, i) => {
            const key = `${arc.origin}|${arc.destination}`;
            const curve = overlapKeys.has(key) ? 0.22 : 0.15;
            return (
              <Line
                key={`req-${i}`}
                coordinates={curveCoords(
                  arc.origin_lng, arc.origin_lat,
                  arc.dest_lng, arc.dest_lat,
                  curve,
                )}
                stroke="#f97316"
                strokeWidth={Math.min(1 + arc.count * 0.2, 2.2)}
                strokeOpacity={Math.min(0.35 + arc.count * 0.08, 0.75)}
                strokeDasharray="4 2.5"
                strokeLinecap="round"
                fill="none"
              />
            );
          })}

          {bookedArcs.map((arc, i) => {
            const key = `${arc.origin}|${arc.destination}`;
            const curve = overlapKeys.has(key) ? 0.08 : 0.15;
            return (
              <Line
                key={`bkd-${i}`}
                coordinates={curveCoords(
                  arc.origin_lng, arc.origin_lat,
                  arc.dest_lng, arc.dest_lat,
                  curve,
                )}
                stroke="#22c55e"
                strokeWidth={Math.min(1.2 + arc.count * 0.25, 2.8)}
                strokeLinecap="round"
                fill="none"
              />
            );
          })}

          {data.cities.map((city) => (
            <Marker
              key={city.name}
              coordinates={[city.lng, city.lat]}
              onMouseEnter={(e: React.MouseEvent) =>
                setTooltip({ name: city.name, volume: city.volume, x: e.clientX, y: e.clientY })
              }
              onMouseLeave={() => setTooltip(null)}
            >
              <circle
                r={radiusScale(city.volume)}
                fill="#3b82f6"
                fillOpacity={0.55}
                stroke="#2563eb"
                strokeWidth={0.6}
              />
              {labeledCities.has(city.name) && (
                <text
                  textAnchor="middle"
                  y={-radiusScale(city.volume) - 3}
                  style={{
                    fontFamily: 'system-ui, -apple-system, sans-serif',
                    fontSize: '7.5px',
                    fontWeight: 600,
                    fill: '#111827',
                    pointerEvents: 'none',
                  }}
                >
                  {city.name.split(',')[0]}
                </text>
              )}
            </Marker>
          ))}
        </ComposableMap>
      </div>

      {/* ─── Summary cards ─── */}
      <div className="mt-5 grid grid-cols-2 sm:grid-cols-4 gap-3">
        <div className="rounded-lg p-3 bg-orange-50/60 border border-orange-200">
          <p className="text-2xl font-semibold text-orange-700 tabular-nums">{requestedArcs.length}</p>
          <p className="text-xs text-orange-500/80 mt-0.5">Requested Lanes</p>
        </div>
        <div className="rounded-lg p-3 bg-emerald-50/60 border border-emerald-200">
          <p className="text-2xl font-semibold text-emerald-700 tabular-nums">{bookedArcs.length}</p>
          <p className="text-xs text-emerald-500/80 mt-0.5">Booked Lanes</p>
        </div>
        <div className="rounded-lg p-3 bg-white border border-gray-200">
          <p className="text-2xl font-semibold text-black tabular-nums">{data.cities.length}</p>
          <p className="text-xs text-gray-400 mt-0.5">Active Cities</p>
        </div>
        <div className="rounded-lg p-3 bg-white border border-gray-200">
          <p className="text-2xl font-semibold text-black tabular-nums">{overlapKeys.size}</p>
          <p className="text-xs text-gray-400 mt-0.5">Overlapping Lanes</p>
        </div>
      </div>

      {/* ─── Collapsible panels ─── */}
      <div className="mt-4 grid grid-cols-1 sm:grid-cols-3 gap-3">
        <Disclosure title="Top Requested Lanes" count={requestedArcs.length}>
          {requestedArcs.length === 0 ? (
            <p className="text-xs text-gray-300 italic pt-2">No data</p>
          ) : (
            <div className="pt-1">
              {requestedArcs.slice(0, 8).map((arc, i) => (
                <LaneRow key={i} arc={arc} maxCount={requestedArcs[0].count} color="orange" />
              ))}
            </div>
          )}
        </Disclosure>

        <Disclosure title="Top Booked Lanes" count={bookedArcs.length}>
          {bookedArcs.length === 0 ? (
            <p className="text-xs text-gray-300 italic pt-2">No data</p>
          ) : (
            <div className="pt-1">
              {bookedArcs.slice(0, 8).map((arc, i) => (
                <LaneRow key={i} arc={arc} maxCount={bookedArcs[0].count} color="green" />
              ))}
            </div>
          )}
        </Disclosure>

        <Disclosure title="Top Hubs" count={sortedCities.length}>
          <div className="pt-2 space-y-1.5">
            {sortedCities.slice(0, 8).map((city, i) => (
              <div key={city.name} className="flex items-center justify-between text-sm">
                <div className="flex items-center gap-2">
                  <span className="w-4 text-right text-gray-300 tabular-nums text-xs">{i + 1}</span>
                  <span className="text-gray-600">{city.name}</span>
                </div>
                <span className="text-black tabular-nums text-xs">{city.volume}</span>
              </div>
            ))}
          </div>
        </Disclosure>
      </div>

      {/* Tooltip */}
      {tooltip && (
        <div
          className="fixed z-50 bg-black text-white text-xs rounded-md px-3 py-1.5 pointer-events-none shadow-lg"
          style={{ left: tooltip.x + 12, top: tooltip.y - 28 }}
        >
          <span className="font-medium">{tooltip.name}</span>
          <span className="text-gray-300 ml-2">{tooltip.volume} loads</span>
        </div>
      )}
    </div>
  );
}
