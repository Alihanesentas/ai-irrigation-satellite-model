/**
 * Types mirrored from the backend contracts this UI renders.
 *
 * `IrrigationMethod` MUST match `agritwin_core.schema.IrrigationMethod`
 * (packages/core/src/agritwin_core/schema.py) exactly - do not invent values.
 *
 * `Recipe` and its nested types MUST match the JSON shape frozen in
 * docs/architecture.md section 4 ("The recipe contract") field-for-field.
 * This app only renders recipes; it never computes or reinterprets them
 * (docs/modules.md#farmer-interface: "Does NOT own: Any computation").
 */

// Mirrors agritwin_core.schema.IrrigationMethod. Keep in sync manually until
// a shared schema package exists across the Python/TS boundary.
export type IrrigationMethod =
  | "sprinkler"
  | "flood"
  | "surface_drip"
  | "subsurface_drip";

export const IRRIGATION_METHODS: { value: IrrigationMethod; label: string }[] = [
  { value: "sprinkler", label: "Yagmurlama" },
  { value: "flood", label: "Salma sulama" },
  { value: "surface_drip", label: "Yuzey damla sulama" },
  { value: "subsurface_drip", label: "Toprak alti damla sulama" },
];

/** A single lat/lng point, GeoJSON-style [lng, lat] is NOT used here on
 * purpose - react-leaflet works in [lat, lng] pairs, so this module stays in
 * that convention and only converts at the data-access boundary if needed. */
export type LatLng = { lat: number; lng: number };

/**
 * PARCEL - client-side skeleton record. Real backend record is
 * `agritwin_core.schema.Parcel` (geometry_wkt, cohort_key, etc.) - this is a
 * deliberately smaller UI-only shape until apps/web talks to packages/api.
 * See lib/data/index.ts for the seam where this gets replaced.
 */
export type Parcel = {
  parcel_id: string;
  name: string;
  boundary: LatLng[]; // polygon ring, drawn by the farmer
  crop: string;
  irrigation_method: IrrigationMethod;
  created_at: string; // ISO 8601 UTC
};

/**
 * ZONE - client-side skeleton record. Real zone delineation is NDVI +
 * SoilGrids derived by the twin (docs/architecture.md#3) and not yet built;
 * for this UI skeleton zones are an even geometric split of the parcel
 * polygon, per the task scope note in docs/delivery-plan.md Phase 1.
 */
export type Zone = {
  zone_id: string;
  parcel_id: string;
  label: string; // e.g. "Bolge 1"
  boundary: LatLng[];
};

// --- Recipe contract mirror (docs/architecture.md#4) ------------------

export type RecipeConfidence = "normal" | "low";
export type FallbackPolicy = "no_irrigation";

export type RecipeEvent = {
  start_utc: string;
  duration_s: number;
  target_mm: number;
  priority: number;
};

export type RecipeZone = {
  zone_id: string;
  events: RecipeEvent[];
};

export type RecipeConstraints = {
  max_concurrent_zones: number;
  min_pressure_kpa: number;
  max_daily_mm: number;
};

export type Recipe = {
  schema_version: string;
  recipe_id: string;
  parcel_id: string;
  issued_at: string;
  valid_from: string;
  valid_until: string;
  confidence: RecipeConfidence;
  fallback_policy: FallbackPolicy;
  zones: RecipeZone[];
  constraints: RecipeConstraints;
  signature: string;
};

/**
 * Local-only farmer response to a recipe. There is deliberately no remote
 * "open valve now" command (docs/architecture.md#11) - approving here only
 * acknowledges the plan in the UI and pings a placeholder backend route;
 * overriding records a request for the decision engine to reconsider next
 * cycle. Neither path actuates anything directly.
 */
export type RecipeDecisionStatus = "pending" | "approved" | "overridden";

export type RecipeDecision = {
  recipe_id: string;
  status: RecipeDecisionStatus;
  decided_at: string;
  override_reason?: string;
};
