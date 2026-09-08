"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { listParcels } from "@/lib/data";
import { IRRIGATION_METHODS } from "@/lib/types";
import type { Parcel } from "@/lib/types";

function methodLabel(method: Parcel["irrigation_method"]): string {
  return IRRIGATION_METHODS.find((m) => m.value === method)?.label ?? method;
}

export default function HomePage() {
  const [parcels, setParcels] = useState<Parcel[] | null>(null);

  useEffect(() => {
    listParcels().then(setParcels);
  }, []);

  return (
    <div className="flex flex-col gap-4">
      <div>
        <h1 className="text-xl font-semibold text-neutral-900">Parsellerim</h1>
        <p className="mt-1 text-sm text-neutral-500">
          Cevrimdisiyken bile en son gorduklerin burada gorunur.
        </p>
      </div>

      {parcels === null && (
        <div className="rounded-xl border border-neutral-200 bg-white p-4 text-sm text-neutral-500">
          Yukleniyor...
        </div>
      )}

      {parcels !== null && parcels.length === 0 && (
        <div className="flex flex-col items-center gap-3 rounded-xl border border-dashed border-brand-200 bg-brand-50 p-6 text-center">
          <p className="text-sm text-neutral-700">
            Henuz kayitli parselin yok. Haritada sinirini cizerek baslayabilirsin.
          </p>
          <Link
            href="/onboarding"
            className="rounded-full bg-brand-500 px-4 py-2 text-sm font-medium text-white active:bg-brand-600"
          >
            Parsel ekle
          </Link>
        </div>
      )}

      <ul className="flex flex-col gap-3">
        {parcels?.map((parcel) => (
          <li key={parcel.parcel_id}>
            <Link
              href={`/parcels/${parcel.parcel_id}`}
              className="block rounded-xl border border-neutral-200 bg-white p-4 shadow-sm active:bg-neutral-50"
            >
              <div className="flex items-center justify-between">
                <span className="font-medium text-neutral-900">{parcel.name}</span>
                <span className="text-xs text-neutral-400">
                  {new Date(parcel.created_at).toLocaleDateString("tr-TR")}
                </span>
              </div>
              <div className="mt-1 flex flex-wrap gap-2 text-xs text-neutral-500">
                <span className="rounded-full bg-neutral-100 px-2 py-0.5">{parcel.crop}</span>
                <span className="rounded-full bg-neutral-100 px-2 py-0.5">
                  {methodLabel(parcel.irrigation_method)}
                </span>
              </div>
            </Link>
          </li>
        ))}
      </ul>
    </div>
  );
}
