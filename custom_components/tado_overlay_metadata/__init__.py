"""Overlay metadata and an explicit timed-OFF action using the existing session."""

import asyncio
from dataclasses import dataclass
from datetime import datetime, timezone
from functools import partial
from time import time
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry, ConfigEntryState
from homeassistant.core import HomeAssistant, ServiceCall, SupportsResponse
from homeassistant.exceptions import (
    ConfigEntryError,
    ConfigEntryNotReady,
    HomeAssistantError,
    ServiceValidationError,
)
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.typing import ConfigType

from .adapter import SourceError, async_validate_source, resolve_client
from .const import CONF_TADO_ENTRY_ID, DOMAIN
from .snapshot import SnapshotError, normalize_response

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


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


TIMED_OFF_SCHEMA = vol.Schema(
    {
        vol.Optional("config_entry_id"): str,
        vol.Required("zone_id"): positive_int,
        vol.Required("expires_at"): positive_int,
    }
)


def set_timed_off(client: Any, zone_id: int, expires_at: int) -> dict[str, Any]:
    """Compute remaining seconds in the executor, just before the cloud write.

    Tado accepts a relative duration, so transport latency can move its server
    deadline by a few seconds. Never create an indefinite OFF on expired input.
    """
    seconds = int(expires_at - time())
    if seconds < 1:
        raise action_error("expiry_passed")
    client.set_zone_overlay(zone_id, "TIMER", duration=seconds, device_type="HEATING", power="OFF")
    return {"zone_id": zone_id, "requested_expires_at": expires_at}


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
    """Register actions independently of loaded config entries."""

    async def capture(call: ServiceCall, *, timed_off: bool = False) -> dict[str, Any]:
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
            try:
                client = resolve_client(hass, entry.data[CONF_TADO_ENTRY_ID])
            except SourceError as err:
                raise action_error(str(err)) from None
            if timed_off:
                try:
                    return await hass.async_add_executor_job(
                        partial(
                            set_timed_off, client, call.data["zone_id"], call.data["expires_at"]
                        )
                    )
                except HomeAssistantError:
                    raise
                except Exception:
                    raise action_error("cannot_write") from None
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
        "restore_timed_off",
        partial(capture, timed_off=True),
        schema=TIMED_OFF_SCHEMA,
        supports_response=SupportsResponse.ONLY,
    )
    hass.services.async_register(
        DOMAIN,
        "capture",
        capture,
        schema=CAPTURE_SCHEMA,
        supports_response=SupportsResponse.ONLY,
    )
    return True


async def async_setup_entry(hass: HomeAssistant, entry: TadoOverlayMetadataConfigEntry) -> bool:
    """Validate the source before enabling actions for this config entry."""
    try:
        await async_validate_source(hass, entry.data[CONF_TADO_ENTRY_ID])
    except SourceError as err:
        key = str(err)
        if key in {"source_not_loaded", "cannot_read"}:
            raise ConfigEntryNotReady(translation_domain=DOMAIN, translation_key=key) from None
        raise ConfigEntryError(translation_domain=DOMAIN, translation_key=key) from None
    entry.runtime_data = Runtime(asyncio.Lock())
    return True


async def async_unload_entry(hass: HomeAssistant, entry: TadoOverlayMetadataConfigEntry) -> bool:
    """Keep the action registered so it can report an informative load error."""
    entry.runtime_data.active = False
    return True
