"""Check the integration's private boundary against the installed Core and Tado."""

import json
from importlib.metadata import version
from importlib.resources import files

from homeassistant.components.tado.coordinator import TadoDataUpdateCoordinator
from homeassistant.config_entries import ConfigEntryState
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.tado_overlay_metadata import async_setup, async_setup_entry
from custom_components.tado_overlay_metadata.adapter import resolve_client
from custom_components.tado_overlay_metadata.const import CONF_TADO_ENTRY_ID, DOMAIN


def test_tado_dependency_matches_core():
    manifest = json.loads(
        files("homeassistant.components.tado").joinpath("manifest.json").read_text()
    )
    assert f"python-tado=={version('python-tado')}" in manifest["requirements"]


async def test_timed_off_with_core_coordinator(hass, source, monkeypatch):
    assert isinstance(source.runtime_data, TadoDataUpdateCoordinator)
    client = source.runtime_data._tado
    assert resolve_client(hass, source.entry_id) is client
    entry = MockConfigEntry(domain=DOMAIN, data={CONF_TADO_ENTRY_ID: source.entry_id})
    entry.add_to_hass(hass)
    await async_setup(hass, {})
    await async_setup_entry(hass, entry)
    entry._async_set_state(hass, ConfigEntryState.LOADED, None)
    monkeypatch.setattr("custom_components.tado_overlay_metadata.time", lambda: 1000)

    result = await hass.services.async_call(
        DOMAIN,
        "restore_timed_off",
        {"zone_id": 1, "expires_at": 1060},
        blocking=True,
        return_response=True,
    )

    assert result == {"zone_id": 1, "requested_expires_at": 1060}
    client.set_zone_overlay.assert_called_once_with(
        1, "TIMER", duration=60, device_type="HEATING", power="OFF"
    )
