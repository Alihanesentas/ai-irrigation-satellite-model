import { NextRequest, NextResponse } from "next/server";

/**
 * PLACEHOLDER route - see approve/route.ts for the full rationale.
 *
 * Records a farmer's objection to a recipe (e.g. "soil is already wet, skip
 * this"). This does NOT reopen or reschedule anything directly - it is a
 * request for the decision engine to reconsider on its next cycle, once
 * that engine exists (Phase 2, packages/decision). Per
 * docs/architecture.md#11 there is no remote valve-actuation path, so an
 * override can never bypass the signed-recipe execution model on the edge
 * node; the farmer's other recourse is manual action at the device itself.
 */
export async function POST(req: NextRequest, { params }: { params: { id: string } }) {
  let reason = "";
  try {
    const body = await req.json();
    reason = typeof body?.reason === "string" ? body.reason : "";
  } catch {
    // no body / invalid JSON - still accept the override with an empty reason
  }

  return NextResponse.json({
    ok: true,
    recipe_id: params.id,
    status: "overridden",
    reason,
    note: "placeholder endpoint - no backend persistence yet, Phase 2 work",
  });
}
