"""HTTP client speaking the device-facing backend contract.

Endpoints (docs/architecture.md#4-5, docs/schemas.md, and the task brief's
"HTTP contract your simulator's client must speak"):

    GET  /devices/{device_id}/recipe            Authorization, If-None-Match
    POST /devices/{device_id}/telemetry         Authorization, Telemetry body
    POST /devices/{device_id}/irrigation-logs   Authorization, IrrigationLog body

Network failures (timeouts, connection errors — including a `FakeBackend`
that raises `httpx.ConnectError` to simulate connectivity loss) are caught
here and converted into explicit, ordinary return values. The device state
machine sits on a safety-critical path (CLAUDE.md rule 6: safe default is
closed) and must be able to treat "backend unreachable" as plain data, not
as an exception it has to remember to catch correctly on every call site.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Literal

import httpx

from agritwin_core.schema import IrrigationLog, Recipe, Telemetry
from agritwin_core.units import require_utc

RecipeStatus = Literal[
    "ok", "not_modified", "not_found", "unauthorized", "forbidden", "unreachable"
]


@dataclass(frozen=True, slots=True)
class RecipePollOutcome:
    """Result of one `GET /devices/{device_id}/recipe` poll.

    `server_time_utc` is populated whenever the backend answered at all
    (200 or 404) — it is the clock-discipline signal from
    docs/schemas.md#telemetry ("the server returns its own time in every
    poll response; devices have no NTP").
    """

    status: RecipeStatus
    server_time_utc: datetime | None
    recipe: Recipe | None


class BackendClient:
    def __init__(
        self,
        base_url: str,
        device_id: str,
        api_key: str,
        *,
        transport: httpx.BaseTransport | None = None,
        timeout: float = 5.0,
    ) -> None:
        self._device_id = device_id
        self._client = httpx.Client(base_url=base_url, transport=transport, timeout=timeout)
        self._auth_header = f"Bearer {api_key}"

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "BackendClient":
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()

    def fetch_recipe(self, if_none_match: str | None = None) -> RecipePollOutcome:
        headers = {"Authorization": self._auth_header}
        if if_none_match:
            headers["If-None-Match"] = f'"{if_none_match}"'
        try:
            resp = self._client.get(f"/devices/{self._device_id}/recipe", headers=headers)
        except httpx.TransportError:
            return RecipePollOutcome("unreachable", None, None)

        if resp.status_code == 401:
            return RecipePollOutcome("unauthorized", None, None)
        if resp.status_code == 403:
            return RecipePollOutcome("forbidden", None, None)
        if resp.status_code == 304:
            return RecipePollOutcome("not_modified", None, None)
        if resp.status_code == 404:
            body = resp.json()
            return RecipePollOutcome("not_found", _parse_server_time(body), None)
        if resp.status_code == 200:
            body = resp.json()
            server_time = _parse_server_time(body)
            raw_recipe = body.get("recipe")
            if raw_recipe is None:
                return RecipePollOutcome("not_found", server_time, None)
            return RecipePollOutcome("ok", server_time, Recipe.model_validate(raw_recipe))
        # Any other status: treat conservatively as unreachable/unusable
        # rather than guessing — never a path to Armed (CLAUDE.md rule 6).
        return RecipePollOutcome("unreachable", None, None)

    def post_telemetry(self, telemetry: Telemetry) -> bool:
        headers = {"Authorization": self._auth_header, "Content-Type": "application/json"}
        try:
            resp = self._client.post(
                f"/devices/{self._device_id}/telemetry",
                headers=headers,
                content=telemetry.model_dump_json(),
            )
        except httpx.TransportError:
            return False
        return resp.status_code == 200

    def post_irrigation_log(self, log: IrrigationLog) -> bool:
        headers = {"Authorization": self._auth_header, "Content-Type": "application/json"}
        try:
            resp = self._client.post(
                f"/devices/{self._device_id}/irrigation-logs",
                headers=headers,
                content=log.model_dump_json(),
            )
        except httpx.TransportError:
            return False
        return resp.status_code == 200


def _parse_server_time(body: dict[str, object]) -> datetime | None:
    raw = body.get("server_time_utc")
    if not isinstance(raw, str):
        return None
    return require_utc(datetime.fromisoformat(raw))
