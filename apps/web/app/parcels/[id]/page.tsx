"use client";

import dynamic from "next/dynamic";
import Link from "next/link";
import { useEffect, useState } from "react";
import { getParcel, listZones } from "@/lib/data";
import { IRRIGATION_METHODS } from "@/lib/types";
import type { Parcel, Zone } from "@/lib/types";

const ParcelMap = dynamic(() => import("@/components/ParcelMap"), {
  ssr: false,
  loading: () => (
    <div className="flex h-56 items-center justify-center rounded-xl border border-neutral-200 bg-neutral-50 text-sm text-neutral-400">
      Harita yukleniyor...
    </div>
  ),
});

const ZONE_COLORS = ["#3f8f3f", "#0e7490", "#b45309", "#7c3aed"];

export default function ParcelDetailPage({ params }: { params: { id: string } }) {
  const [parcel, setParcel] = useState<Parcel | null | undefined>(undefined);
  const [zones, setZones] = useState<Zone[]>([]);

  useEffect(() => {
    getParcel(params.id).then(setParcel);
    listZones(params.id).then(setZones);
  }, [params.id]);

  if (parcel === undefined) {
    return <p className="text-sm text-neutral-500">Yukleniyor...</p>;
  }

  if (parcel === null) {
    return (
      <div className="rounded-xl border border-neutral-200 bg-white p-4 text-sm text-neutral-600">
        Bu parsel bulunamadi. Cevrimdisiysan, daha once bu cihazda goruntulenmemis olabilir.
        <div className="mt-3">
          <Link href="/" className="text-brand-600 underline">
            Parsellerime don
          </Link>
        </div>
      </div>
    );
  }

  const methodLabel =
    IRRIGATION_METHODS.find((m) => m.value === parcel.irrigation_method)?.label ??
    parcel.irrigation_method;

  return (
    <div className="flex flex-col gap-5">
      <div>
        <h1 className="text-xl font-semibold text-neutral-900">{parcel.name}</h1>
        <div className="mt-1 flex flex-wrap gap-2 text-xs text-neutral-500">
          <span className="rounded-full bg-neutral-100 px-2 py-0.5">{parcel.crop}</span>
          <span className="rounded-full bg-neutral-100 px-2 py-0.5">{methodLabel}</span>
        </div>
      </div>

      <ParcelMap value={parcel.boundary} readOnly />

      <div>
        <h2 className="mb-2 text-sm font-semibold text-neutral-800">
          Sulama bolgeleri ({zones.length})
        </h2>
        <p className="mb-3 text-xs text-neutral-500">
          Bolgeler uydu verisinden (NDVI ve toprak haritalari) otomatik cikarilir; bu ekranda
          gosterilen bolunum baslangic icin basitlestirilmis bir tahmindir.
        </p>
        <ul className="flex flex-col gap-2">
          {zones.map((zone, i) => (
            <li
              key={zone.zone_id}
              className="flex items-center justify-between rounded-xl border border-neutral-200 bg-white p-3"
            >
              <div className="flex items-center gap-3">
                <span
                  className="h-3 w-3 rounded-full"
                  style={{ backgroundColor: ZONE_COLORS[i % ZONE_COLORS.length] }}
                />
                <span className="text-sm font-medium text-neutral-800">{zone.label}</span>
              </div>
              <span className="text-xs text-neutral-400">{zone.zone_id}</span>
            </li>
          ))}
          {zones.length === 0 && (
            <li className="rounded-xl border border-dashed border-neutral-200 p-3 text-sm text-neutral-400">
              Bu parsel icin henuz bolge tanimlanmadi.
            </li>
          )}
        </ul>
      </div>

      <Link
        href={`/parcels/${parcel.parcel_id}/recipe`}
        className="rounded-full bg-brand-500 px-4 py-3 text-center text-sm font-semibold text-white active:bg-brand-600"
      >
        Sulama recetesini goruntule
      </Link>
    </div>
  );
}
