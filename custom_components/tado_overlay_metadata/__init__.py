"""Read-only overlay metadata using Home Assistant's existing Tado session."""

import asyncio
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry, ConfigEntryState
from homeassistant.core import HomeAssistant, ServiceCall, SupportsResponse
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers.typing import ConfigType

from .const import CONF_TADO_ENTRY_ID, DOMAIN, SOURCE_DOMAIN
from .snapshot import SnapshotError, normalize_response


def positive_int(value: Any) -> int:
    """Do not accept booleans or silently truncate fractional zone IDs."""
    if type(value) is not int or value < 1:
        raise vol.Invalid("Expected a positive integer zone ID")
    return value


CAPTURE_SCHEMA = vol.Schema(
    {
        vol.Optional("config_entry_id"): str,
        vol.Optional("zone_ids"): vol.All([positive_int], vol.Length(min=1, max=100)),
    }
)


@dataclass
class Runtime:
    """No credentials or cloud state are cached in this integration."""

    lock: asyncio.Lock
    active: bool = True


type TadoOverlayMetadataConfigEntry = ConfigEntry[Runtime]


def action_error(key: str) -> HomeAssistantError:
    """Keep action errors translated and independent of vendor exception text."""
    return HomeAssistantError(translation_domain=DOMAIN, translation_key=key)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Register actions independently of loaded entries, as required by HA."""

    async def capture(call: ServiceCall) -> dict[str, Any]:
        active = {
            entry.entry_id: entry
            for entry in hass.config_entries.async_entries(DOMAIN)
            if entry.state == ConfigEntryState.LOADED
            and isinstance(getattr(entry, "runtime_data", None), Runtime)
            and entry.runtime_data.active
        }
        requested = call.data.get("config_entry_id")
        if requested is None:
            if len(active) != 1:
                raise ServiceValidationError(
                    translation_domain=DOMAIN, translation_key="select_entry"
                )
            requested = next(iter(active))
        entry = active.get(requested)
        if entry is None:
            raise ServiceValidationError(
                translation_domain=DOMAIN, translation_key="entry_not_loaded"
            )
        runtime = entry.runtime_data
        async with runtime.lock:
            # Resolve again after acquiring the lock: entries can unload or the
            # source coordinator can be replaced while another request runs.
            entry = hass.config_entries.async_get_entry(requested)
            if (
                entry is None
                or entry.state != ConfigEntryState.LOADED
                or getattr(entry, "runtime_data", None) is not runtime
                or not runtime.active
            ):
                raise action_error("entry_not_loaded")
            source = hass.config_entries.async_get_entry(entry.data[CONF_TADO_ENTRY_ID])
            if (
                source is None
                or source.domain != SOURCE_DOMAIN
                or source.state != ConfigEntryState.LOADED
            ):
                raise action_error("source_not_loaded")
            coordinator = getattr(source, "runtime_data", None)
            # Intentionally narrow private dependency, reviewed against HA
            # 2026.9.0 / python-tado 0.18.16. Never read or export refresh tokens.
            client = getattr(coordinator, "_tado", None)
            if client is None:
                raise action_error("incompatible_source")
            try:
                response = await hass.async_add_executor_job(client.get_zone_states)
            except Exception:
                # Vendor exceptions can contain URLs or session information.
                raise action_error("cannot_read") from None
            if not runtime.active:
                raise action_error("entry_not_loaded")
            try:
                result = normalize_response(response, call.data.get("zone_ids"))
            except SnapshotError:
                raise action_error("unsupported_response") from None
        return {"captured_at": datetime.now(timezone.utc).isoformat(), **result}

    hass.services.async_register(
        DOMAIN,
        "capture",
        capture,
        schema=CAPTURE_SCHEMA,
        supports_response=SupportsResponse.ONLY,
    )
    return True


async def async_setup_entry(hass: HomeAssistant, entry: TadoOverlayMetadataConfigEntry) -> bool:
    """Register local runtime only; no startup cloud request or heating command."""
    entry.runtime_data = Runtime(asyncio.Lock())
    return True


async def async_unload_entry(hass: HomeAssistant, entry: TadoOverlayMetadataConfigEntry) -> bool:
    """Keep the action registered so it can report an informative load error."""
    entry.runtime_data.active = False
    return True
