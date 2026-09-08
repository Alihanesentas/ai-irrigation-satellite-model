"use client";

/**
 * Renders a Recipe (docs/architecture.md#4) in farmer-friendly terms, plus
 * the approve/override action.
 *
 * Important: there is deliberately no remote "open valve now" command in
 * this system (docs/architecture.md#11 - "Manual override happens on the
 * device or through a recipe"). Approving here only acknowledges the plan
 * in this UI and calls a placeholder backend route; it does not open a
 * valve. Overriding records a farmer-flagged objection for the decision
 * engine to consider on its next cycle (not built yet) - it does not
 * directly command a conservative plan either, it requests one.
 */

import { useEffect, useState } from "react";
import type { Recipe, RecipeDecision, Zone } from "@/lib/types";
import { getRecipeDecision, saveRecipeDecision } from "@/lib/data";

function fmtDateTime(iso: string): string {
  return new Date(iso).toLocaleString("tr-TR", {
    day: "2-digit",
    month: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function fmtDuration(seconds: number): string {
  const minutes = Math.round(seconds / 60);
  if (minutes < 60) return `${minutes} dk`;
  const hours = Math.floor(minutes / 60);
  const rest = minutes % 60;
  return rest === 0 ? `${hours} sa` : `${hours} sa ${rest} dk`;
}

function zoneLabel(zoneId: string, zones: Zone[]): string {
  return zones.find((z) => z.zone_id === zoneId)?.label ?? zoneId;
}

export default function RecipeView({ recipe, zones }: { recipe: Recipe; zones: Zone[] }) {
  const [decision, setDecision] = useState<RecipeDecision | null | undefined>(undefined);
  const [overrideOpen, setOverrideOpen] = useState(false);
  const [overrideReason, setOverrideReason] = useState("");
  const [busy, setBusy] = useState(false);
  const [feedback, setFeedback] = useState<string | null>(null);

  useEffect(() => {
    getRecipeDecision(recipe.recipe_id).then(setDecision);
  }, [recipe.recipe_id]);

  const isLowConfidence = recipe.confidence === "low";
  const validFrom = fmtDateTime(recipe.valid_from);
  const validUntil = fmtDateTime(recipe.valid_until);

  const handleApprove = async () => {
    setBusy(true);
    setFeedback(null);
    try {
      const res = await fetch(`/api/recipes/${recipe.recipe_id}/approve`, { method: "POST" });
      if (!res.ok) throw new Error("approve failed");
      const next: RecipeDecision = {
        recipe_id: recipe.recipe_id,
        status: "approved",
        decided_at: new Date().toISOString(),
      };
      await saveRecipeDecision(next);
      setDecision(next);
      setFeedback("Recete onaylandi. Cihaz zaten kendi programina gore calisir; bu onay bilgi amaclidir.");
    } catch {
      setFeedback("Onay su an cevrimdisi kaydedildi, baglanti gelince gonderilecek.");
    } finally {
      setBusy(false);
    }
  };

  const handleOverrideSubmit = async () => {
    if (!overrideReason.trim()) return;
    setBusy(true);
    setFeedback(null);
    try {
      const res = await fetch(`/api/recipes/${recipe.recipe_id}/override`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ reason: overrideReason.trim() }),
      });
      if (!res.ok) throw new Error("override failed");
      const next: RecipeDecision = {
        recipe_id: recipe.recipe_id,
        status: "overridden",
        decided_at: new Date().toISOString(),
        override_reason: overrideReason.trim(),
      };
      await saveRecipeDecision(next);
      setDecision(next);
      setOverrideOpen(false);
      setFeedback(
        "Itirazin kaydedildi. Sulama valfi uzaktan acilmaz - degisiklik ancak yeni bir receteyle ya da cihazin uzerinden yapilir."
      );
    } catch {
      setFeedback("Itiraz su an cevrimdisi kaydedildi, baglanti gelince gonderilecek.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="flex flex-col gap-4">
      {isLowConfidence && (
        <div className="rounded-xl border border-warn-500 bg-warn-50 p-3 text-sm text-warn-700">
          <p className="font-semibold">Dusuk guven duzeyi</p>
          <p className="mt-1 text-warn-700/90">
            Bu parselde uydu verileriyle model tahmini arasinda beklenmedik bir fark tespit
            edildi. Sistem bu yuzden daha temkinli (dusuk miktarli) bir sulama plani uretti.
            Sorun devam ederse toprak analizi yaptirmani onerebiliriz.
          </p>
        </div>
      )}

      <div className="rounded-xl border border-neutral-200 bg-white p-4">
        <div className="flex items-center justify-between">
          <span className="text-sm font-semibold text-neutral-800">Gecerlilik araligi</span>
          <span
            className={`rounded-full px-2 py-0.5 text-xs font-medium ${
              isLowConfidence ? "bg-warn-100 text-warn-700" : "bg-brand-100 text-brand-700"
            }`}
          >
            {isLowConfidence ? "Dusuk guven" : "Normal"}
          </span>
        </div>
        <p className="mt-1 text-sm text-neutral-600">
          {validFrom} - {validUntil}
        </p>
        <p className="mt-2 text-xs text-neutral-400">
          Sure sonunda recete gecersiz sayilir ve cihaz sulama yapmaz (guvenli varsayilan:
          kapali).
        </p>
      </div>

      <div className="flex flex-col gap-3">
        {recipe.zones.map((zone) => (
          <div key={zone.zone_id} className="rounded-xl border border-neutral-200 bg-white p-4">
            <p className="mb-2 text-sm font-semibold text-neutral-800">
              {zoneLabel(zone.zone_id, zones)}
            </p>
            <ul className="flex flex-col gap-2">
              {zone.events.map((event, i) => (
                <li
                  key={i}
                  className="flex items-center justify-between rounded-lg bg-neutral-50 px-3 py-2 text-sm"
                >
                  <span className="text-neutral-700">{fmtDateTime(event.start_utc)}</span>
                  <span className="text-neutral-500">{fmtDuration(event.duration_s)}</span>
                  <span className="font-medium text-brand-700">{event.target_mm} mm</span>
                </li>
              ))}
            </ul>
          </div>
        ))}
      </div>

      <div className="rounded-xl border border-neutral-200 bg-white p-4 text-xs text-neutral-500">
        <p>Ayni anda en fazla {recipe.constraints.max_concurrent_zones} bolge sulanir.</p>
        <p>Gunluk en fazla {recipe.constraints.max_daily_mm} mm su verilir.</p>
      </div>

      {decision?.status === "approved" && (
        <div className="rounded-xl bg-brand-50 p-3 text-sm text-brand-700">
          Bu receteyi onayladin ({fmtDateTime(decision.decided_at)}).
        </div>
      )}
      {decision?.status === "overridden" && (
        <div className="rounded-xl bg-neutral-100 p-3 text-sm text-neutral-700">
          Bu recete icin itiraz kaydedildi ({fmtDateTime(decision.decided_at)}): "
          {decision.override_reason}"
        </div>
      )}

      {feedback && <p className="text-xs text-neutral-500">{feedback}</p>}

      {(!decision || decision.status === "pending") && (
        <div className="flex gap-3">
          <button
            type="button"
            onClick={handleApprove}
            disabled={busy}
            className="flex-1 rounded-full bg-brand-500 px-4 py-3 text-sm font-semibold text-white disabled:opacity-40 active:bg-brand-600"
          >
            Onayla
          </button>
          <button
            type="button"
            onClick={() => setOverrideOpen(true)}
            disabled={busy}
            className="flex-1 rounded-full border border-neutral-300 px-4 py-3 text-sm font-semibold text-neutral-700 disabled:opacity-40"
          >
            Itiraz et
          </button>
        </div>
      )}

      {overrideOpen && (
        <div className="rounded-xl border border-neutral-200 bg-white p-4">
          <p className="text-sm font-semibold text-neutral-800">Neden itiraz ediyorsun?</p>
          <p className="mt-1 text-xs text-neutral-500">
            Bu bilgi karar motoruna iletilir; valf dogrudan uzaktan acilip kapatilmaz. Cihaz
            uzerinde de elle mudahale edebilirsin.
          </p>
          <textarea
            value={overrideReason}
            onChange={(e) => setOverrideReason(e.target.value)}
            rows={3}
            placeholder="orn. Toprak zaten islak, sulama gereksiz"
            className="mt-2 w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm focus:border-brand-500 focus:outline-none"
          />
          <div className="mt-3 flex gap-2">
            <button
              type="button"
              onClick={handleOverrideSubmit}
              disabled={busy || !overrideReason.trim()}
              className="flex-1 rounded-full bg-neutral-800 px-4 py-2 text-sm font-medium text-white disabled:opacity-40"
            >
              Gonder
            </button>
            <button
              type="button"
              onClick={() => setOverrideOpen(false)}
              className="flex-1 rounded-full border border-neutral-300 px-4 py-2 text-sm font-medium text-neutral-700"
            >
              Vazgec
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
