"""Access the built-in Tado session and validate the overlay API contract."""

from typing import Any

from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant

from .const import SOURCE_DOMAIN
from .snapshot import SnapshotError, normalize_response


class SourceError(Exception):
    """A source failure identified by a translation key, without vendor details."""


def resolve_client(hass: HomeAssistant, source_id: str) -> Any:
    """Resolve the current client so source reloads cannot leave a cached session."""
    source = hass.config_entries.async_get_entry(source_id)
    if source is None or source.domain != SOURCE_DOMAIN:
        raise SourceError("source_missing")
    if source.state != ConfigEntryState.LOADED:
        raise SourceError("source_not_loaded")
    # Core's Tado coordinator exposes the python-tado client through _tado.
    client = getattr(getattr(source, "runtime_data", None), "_tado", None)
    if not all(
        callable(getattr(client, method, None))
        for method in ("get_zone_states", "set_zone_overlay")
    ):
        raise SourceError("incompatible_source")
    return client


async def async_validate_source(hass: HomeAssistant, source_id: str) -> None:
    """Test a read without changing heating or retaining cloud payloads."""
    client = resolve_client(hass, source_id)
    try:
        response = await hass.async_add_executor_job(client.get_zone_states)
    except Exception:
        # Vendor exception messages can contain authentication or request details.
        raise SourceError("cannot_read") from None
    if resolve_client(hass, source_id) is not client:
        raise SourceError("source_not_loaded")
    try:
        normalize_response(response, None)
    except SnapshotError:
        raise SourceError("unsupported_response") from None
