"use client";

/**
 * Parcel boundary drawing map.
 *
 * Uses react-leaflet + OpenStreetMap raster tiles (no API key, no paid
 * service - "boring technology wins", CLAUDE.md rule 4). Drawing is a
 * minimal custom tap-to-add-vertex interaction rather than pulling in
 * leaflet-draw, to keep the dependency surface small for a UI skeleton.
 */

import { MapContainer, TileLayer, Polygon, Marker, useMapEvents } from "react-leaflet";
import { useMemo, useState } from "react";
import L from "leaflet";
import type { LatLng } from "@/lib/types";

// Leaflet's default marker icons reference image files that don't resolve
// correctly under Next.js bundling; use a small inline SVG divIcon instead.
const vertexIcon = L.divIcon({
  className: "",
  html: '<div style="width:10px;height:10px;border-radius:9999px;background:#3f8f3f;border:2px solid white;box-shadow:0 0 0 1px #3f8f3f;"></div>',
  iconSize: [10, 10],
  iconAnchor: [5, 5],
});

// Default view: rural Konya, Turkey - arbitrary, just a reasonable starting
// centre for a Turkish farmer testing the app.
const DEFAULT_CENTER: [number, number] = [37.8746, 32.4932];
const DEFAULT_ZOOM = 15;

function ClickToAddVertex({ onAdd }: { onAdd: (p: LatLng) => void }) {
  useMapEvents({
    click(e) {
      onAdd({ lat: e.latlng.lat, lng: e.latlng.lng });
    },
  });
  return null;
}

export default function ParcelMap({
  value,
  onChange,
  readOnly = false,
}: {
  value: LatLng[];
  onChange?: (points: LatLng[]) => void;
  readOnly?: boolean;
}) {
  const positions = useMemo<[number, number][]>(
    () => value.map((p) => [p.lat, p.lng]),
    [value]
  );

  const handleAdd = (p: LatLng) => {
    if (readOnly || !onChange) return;
    onChange([...value, p]);
  };

  const handleUndo = () => {
    if (!onChange) return;
    onChange(value.slice(0, -1));
  };

  const handleClear = () => {
    if (!onChange) return;
    onChange([]);
  };

  return (
    <div className="flex flex-col gap-2">
      <div className="h-72 w-full overflow-hidden rounded-xl border border-neutral-200">
        <MapContainer
          center={positions[0] ?? DEFAULT_CENTER}
          zoom={DEFAULT_ZOOM}
          scrollWheelZoom
          style={{ height: "100%", width: "100%" }}
        >
          <TileLayer
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          />
          {!readOnly && <ClickToAddVertex onAdd={handleAdd} />}
          {positions.length >= 3 && (
            <Polygon
              positions={positions}
              pathOptions={{ color: "#3f8f3f", fillOpacity: 0.25 }}
            />
          )}
          {!readOnly &&
            value.map((p, i) => (
              <Marker key={i} position={[p.lat, p.lng]} icon={vertexIcon} />
            ))}
        </MapContainer>
      </div>

      {!readOnly && (
        <div className="flex items-center justify-between gap-2">
          <p className="text-xs text-neutral-500">
            {value.length < 3
              ? `Sinir icin haritaya dokun (en az 3 nokta) - ${value.length} nokta eklendi`
              : `${value.length} nokta - sinir hazir`}
          </p>
          <div className="flex gap-2">
            <button
              type="button"
              onClick={handleUndo}
              disabled={value.length === 0}
              className="rounded-full border border-neutral-300 px-3 py-1 text-xs font-medium text-neutral-700 disabled:opacity-40"
            >
              Geri al
            </button>
            <button
              type="button"
              onClick={handleClear}
              disabled={value.length === 0}
              className="rounded-full border border-neutral-300 px-3 py-1 text-xs font-medium text-neutral-700 disabled:opacity-40"
            >
              Temizle
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
