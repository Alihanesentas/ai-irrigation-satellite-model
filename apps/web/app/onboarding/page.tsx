"use client";

import dynamic from "next/dynamic";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { createParcel, attachFixtureRecipeToParcel } from "@/lib/data";
import { IRRIGATION_METHODS } from "@/lib/types";
import type { IrrigationMethod, LatLng } from "@/lib/types";

// Leaflet touches `window` at import time, so it cannot be server-rendered.
const ParcelMap = dynamic(() => import("@/components/ParcelMap"), {
  ssr: false,
  loading: () => (
    <div className="flex h-72 items-center justify-center rounded-xl border border-neutral-200 bg-neutral-50 text-sm text-neutral-400">
      Harita yukleniyor...
    </div>
  ),
});

export default function OnboardingPage() {
  const router = useRouter();
  const [boundary, setBoundary] = useState<LatLng[]>([]);
  const [name, setName] = useState("");
  const [crop, setCrop] = useState("");
  const [method, setMethod] = useState<IrrigationMethod>("surface_drip");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const canSubmit = boundary.length >= 3 && name.trim() && crop.trim() && !submitting;

  const handleSubmit = async () => {
    if (!canSubmit) return;
    setSubmitting(true);
    setError(null);
    try {
      const parcel = await createParcel({
        name: name.trim(),
        crop: crop.trim(),
        irrigation_method: method,
        boundary,
      });
      // Demo-only: attach a fixture recipe so "view recipe" is not empty.
      // Real recipes come from the decision engine (not built yet, Phase 2).
      await attachFixtureRecipeToParcel(parcel.parcel_id);
      router.push(`/parcels/${parcel.parcel_id}`);
    } catch (e) {
      setError("Parsel kaydedilirken bir sorun olustu. Tekrar dene.");
      setSubmitting(false);
    }
  };

  return (
    <div className="flex flex-col gap-5">
      <div>
        <h1 className="text-xl font-semibold text-neutral-900">Yeni parsel ekle</h1>
        <p className="mt-1 text-sm text-neutral-500">
          Once haritada parselinin sinirini ciz, sonra bilgilerini gir.
        </p>
      </div>

      <ParcelMap value={boundary} onChange={setBoundary} />

      <div className="flex flex-col gap-4 rounded-xl border border-neutral-200 bg-white p-4">
        <label className="flex flex-col gap-1">
          <span className="text-sm font-medium text-neutral-700">Parsel adi</span>
          <input
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="orn. Guney tarla"
            className="rounded-lg border border-neutral-300 px-3 py-2 text-sm focus:border-brand-500 focus:outline-none"
          />
        </label>

        <label className="flex flex-col gap-1">
          <span className="text-sm font-medium text-neutral-700">Urun / bitki</span>
          <input
            type="text"
            value={crop}
            onChange={(e) => setCrop(e.target.value)}
            placeholder="orn. Domates"
            className="rounded-lg border border-neutral-300 px-3 py-2 text-sm focus:border-brand-500 focus:outline-none"
          />
        </label>

        <div className="flex flex-col gap-1">
          <span className="text-sm font-medium text-neutral-700">Sulama yontemi</span>
          <div className="grid grid-cols-2 gap-2">
            {IRRIGATION_METHODS.map((m) => (
              <button
                key={m.value}
                type="button"
                onClick={() => setMethod(m.value)}
                className={`rounded-lg border px-3 py-2 text-sm ${
                  method === m.value
                    ? "border-brand-500 bg-brand-50 font-medium text-brand-700"
                    : "border-neutral-300 text-neutral-600"
                }`}
              >
                {m.label}
              </button>
            ))}
          </div>
        </div>
      </div>

      {error && <p className="text-sm text-red-600">{error}</p>}

      <button
        type="button"
        onClick={handleSubmit}
        disabled={!canSubmit}
        className="rounded-full bg-brand-500 px-4 py-3 text-sm font-semibold text-white disabled:opacity-40 active:bg-brand-600"
      >
        {submitting ? "Kaydediliyor..." : "Parseli kaydet"}
      </button>
    </div>
  );
}
