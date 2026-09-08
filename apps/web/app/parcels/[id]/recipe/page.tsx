"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { getParcel, getRecipe, listZones } from "@/lib/data";
import RecipeView from "@/components/RecipeView";
import type { Parcel, Recipe, Zone } from "@/lib/types";

export default function RecipePage({ params }: { params: { id: string } }) {
  const [parcel, setParcel] = useState<Parcel | null | undefined>(undefined);
  const [recipe, setRecipe] = useState<Recipe | null | undefined>(undefined);
  const [zones, setZones] = useState<Zone[]>([]);

  useEffect(() => {
    getParcel(params.id).then(setParcel);
    getRecipe(params.id).then(setRecipe);
    listZones(params.id).then(setZones);
  }, [params.id]);

  if (parcel === undefined || recipe === undefined) {
    return <p className="text-sm text-neutral-500">Yukleniyor...</p>;
  }

  if (!parcel) {
    return (
      <div className="rounded-xl border border-neutral-200 bg-white p-4 text-sm text-neutral-600">
        Bu parsel bulunamadi.
        <div className="mt-3">
          <Link href="/" className="text-brand-600 underline">
            Parsellerime don
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-4">
      <div>
        <Link href={`/parcels/${parcel.parcel_id}`} className="text-xs text-brand-600 underline">
          &larr; {parcel.name}
        </Link>
        <h1 className="mt-1 text-xl font-semibold text-neutral-900">Sulama recetesi</h1>
      </div>

      {!recipe && (
        <div className="rounded-xl border border-dashed border-neutral-200 p-4 text-sm text-neutral-500">
          Bu parsel icin henuz bir recete yayinlanmadi. Karar motoru calismaya basladiginda
          ilk recete burada gorunecek.
        </div>
      )}

      {recipe && <RecipeView recipe={recipe} zones={zones} />}
    </div>
  );
}
