"""Normalize classic Tado heating overlays without HA or network dependencies."""

from datetime import datetime
from math import isfinite
from typing import Any


class SnapshotError(ValueError):
    """A zone cannot be represented safely for subsequent restoration."""


def timestamp(value: Any) -> int:
    """Require an absolute expiry; never derive a fresh duration from now."""
    if not isinstance(value, str):
        raise SnapshotError("missing_expiry")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            raise SnapshotError("expiry_without_timezone")
        return int(parsed.timestamp())
    except (ValueError, OverflowError, OSError) as err:
        if isinstance(err, SnapshotError):
            raise
        raise SnapshotError("invalid_expiry") from None


def normalize(raw: Any) -> dict[str, Any]:
    """Return a small, versioned snapshot containing no account/device fields."""
    if not isinstance(raw, dict) or not isinstance(raw.get("setting"), dict):
        raise SnapshotError("invalid_zone")
    if raw["setting"].get("type") != "HEATING":
        raise SnapshotError("unsupported_zone_type")
    if "overlay" not in raw:
        raise SnapshotError("missing_overlay")
    overlay = raw["overlay"]
    if overlay is None:
        return {
            "version": 1,
            "mode": "auto",
            "temperature": None,
            "termination": "SCHEDULE",
            "expires_at": None,
        }
    if not isinstance(overlay, dict):
        raise SnapshotError("invalid_overlay")
    setting = overlay.get("setting")
    termination = overlay.get("termination")
    if not isinstance(setting, dict) or setting.get("type") != "HEATING":
        raise SnapshotError("unsupported_overlay_type")
    if not isinstance(termination, dict):
        raise SnapshotError("missing_termination")
    kind = termination.get("type")
    if not isinstance(kind, str) or kind not in {"MANUAL", "TADO_MODE", "NEXT_TIME_BLOCK", "TIMER"}:
        raise SnapshotError("unsupported_termination")
    expiry = None
    if kind != "MANUAL":
        # projectedExpiry is accepted when provided by Tado. Its availability
        # for the user's next-block overrides still needs live verification.
        value = termination.get("expiry")
        if value is None:
            value = termination.get("projectedExpiry")
        expiry = timestamp(value)
    power = setting.get("power")
    if power not in ("ON", "OFF"):
        raise SnapshotError("unsupported_power")
    temperature = None
    if power == "ON":
        temp = setting.get("temperature")
        if not isinstance(temp, dict):
            raise SnapshotError("invalid_temperature")
        temperature = temp.get("celsius")
        if (
            isinstance(temperature, bool)
            or not isinstance(temperature, (int, float))
            or not isfinite(temperature)
        ):
            raise SnapshotError("invalid_temperature")
    return {
        "version": 1,
        "mode": "heat" if power == "ON" else "off",
        "temperature": temperature,
        "termination": kind,
        "expires_at": expiry,
    }


def normalize_response(response: Any, zone_ids: list[int] | None) -> dict[str, Any]:
    """Isolate per-zone failures and exclude unrequested zones."""
    raw_zones = response.get("zoneStates") if isinstance(response, dict) else None
    if not isinstance(raw_zones, dict) or not raw_zones:
        raise SnapshotError("invalid_zone_response")
    if zone_ids is None:
        if any(
            not isinstance(key, str) or not key.isdecimal() or int(key) < 1 for key in raw_zones
        ):
            raise SnapshotError("invalid_zone_response")
        keys = sorted(raw_zones, key=int)
    else:
        keys = list(dict.fromkeys(str(zone_id) for zone_id in zone_ids))
    snapshots, errors = {}, {}
    for key in keys:
        try:
            snapshots[key] = normalize(raw_zones.get(key))
        except SnapshotError as err:
            errors[key] = str(err)
    return {"snapshots": snapshots, "errors": errors}
