import { NextRequest, NextResponse } from "next/server";

/**
 * PLACEHOLDER route. Real backend wiring is Phase 2 - the decision engine
 * (packages/decision) does not exist yet (docs/modules.md: "not started"),
 * and there is no farmer-facing persistence backend either
 * (docs/architecture.md#11 notes only device<->backend and recipe signing
 * boundaries are defined so far).
 *
 * This currently just echoes success so the UI has a real network round
 * trip to call during development/testing. It does not persist anything
 * server-side and, critically, does NOT actuate a valve - per
 * docs/architecture.md#11 there is deliberately no remote "open valve now"
 * command in this system. Approval here is an acknowledgement only; the
 * source of truth for what the edge node executes remains the signed
 * recipe itself.
 */
export async function POST(_req: NextRequest, { params }: { params: { id: string } }) {
  return NextResponse.json({
    ok: true,
    recipe_id: params.id,
    status: "approved",
    note: "placeholder endpoint - no backend persistence yet, Phase 2 work",
  });
}
