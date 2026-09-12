"""Validate startup failures and action lifecycle against Home Assistant APIs."""

from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from homeassistant.config_entries import ConfigEntryState
from homeassistant.exceptions import ConfigEntryError, ConfigEntryNotReady, HomeAssistantError
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.tado_overlay_metadata import (
    async_setup,
    async_setup_entry,
    async_unload_entry,
)
from custom_components.tado_overlay_metadata.const import CONF_TADO_ENTRY_ID, DOMAIN

from .conftest import RAW


@pytest.fixture
def metadata(hass, source):
    entry = MockConfigEntry(domain=DOMAIN, data={CONF_TADO_ENTRY_ID: source.entry_id})
    entry.add_to_hass(hass)
    return entry


async def test_setup_and_unload(hass, source, metadata):
    assert await async_setup(hass, {})
    assert await async_setup_entry(hass, metadata)
    source.runtime_data._tado.get_zone_states.assert_called_once_with()
    source.runtime_data._tado.set_zone_overlay.assert_not_called()
    metadata._async_set_state(hass, ConfigEntryState.LOADED, None)
    result = await hass.services.async_call(
        DOMAIN, "capture", {}, blocking=True, return_response=True
    )
    assert result["snapshots"]["1"]["mode"] == "auto"
    assert await async_unload_entry(hass, metadata)
    assert hass.services.has_service(DOMAIN, "capture")
    assert hass.services.has_service(DOMAIN, "restore_timed_off")
    with pytest.raises(HomeAssistantError):
        await hass.services.async_call(DOMAIN, "capture", {}, blocking=True, return_response=True)


@pytest.mark.parametrize("failure", ["unloaded", "network", "incompatible", "malformed", "missing"])
async def test_setup_failure(hass, source, metadata, failure):
    if failure == "unloaded":
        source._async_set_state(hass, ConfigEntryState.NOT_LOADED, None)
    elif failure == "network":
        source.runtime_data._tado.get_zone_states.side_effect = RuntimeError(
            "private vendor detail"
        )
    elif failure == "incompatible":
        source.runtime_data = None
    elif failure == "malformed":
        source.runtime_data._tado.get_zone_states.return_value = {}
    else:
        hass.config_entries.async_update_entry(metadata, data={CONF_TADO_ENTRY_ID: "missing"})
    error = ConfigEntryNotReady if failure in {"unloaded", "network"} else ConfigEntryError
    with pytest.raises(error) as caught:
        await async_setup_entry(hass, metadata)
    assert "private vendor detail" not in str(caught.value)
    assert not hasattr(metadata, "runtime_data")


async def test_source_changes_during_validation(hass, source, metadata):
    def replace_source():
        source.runtime_data = SimpleNamespace(_tado=Mock())
        return RAW

    source.runtime_data._tado.get_zone_states.side_effect = replace_source
    with pytest.raises(ConfigEntryNotReady):
        await async_setup_entry(hass, metadata)


async def test_source_reload(hass, source, metadata):
    await async_setup(hass, {})
    await async_setup_entry(hass, metadata)
    metadata._async_set_state(hass, ConfigEntryState.LOADED, None)
    replacement = Mock(get_zone_states=Mock(return_value=RAW))
    source.runtime_data = SimpleNamespace(_tado=replacement)
    await hass.services.async_call(DOMAIN, "capture", {}, blocking=True, return_response=True)
    replacement.get_zone_states.assert_called_once_with()
