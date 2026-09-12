"""Exercise configuration, recovery and duplicate handling through Home Assistant."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.config_entries import ConfigEntryState
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.tado_overlay_metadata.const import CONF_TADO_ENTRY_ID, DOMAIN

RAW = {"zoneStates": {"1": {"setting": {"type": "HEATING"}, "overlay": None}}}


@pytest.fixture
def setup_entry():
    """Keep successful flow tests independent of the entry setup tests."""
    with patch(
        "custom_components.tado_overlay_metadata.async_setup_entry",
        new_callable=AsyncMock,
        return_value=True,
    ) as mock:
        yield mock


async def start(hass):
    return await hass.config_entries.flow.async_init(DOMAIN, context={"source": "user"})


async def test_no_source(hass):
    result = await start(hass)
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "no_tado"


async def test_unloaded_source(hass, source):
    source._async_set_state(hass, ConfigEntryState.NOT_LOADED, None)
    assert (await start(hass))["reason"] == "no_tado"


async def test_success(hass, source, setup_entry):
    result = await start(hass)
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {}
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_TADO_ENTRY_ID: source.entry_id}
    )
    await hass.async_block_till_done()
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Tado Overlay Metadata: Tado home"
    assert result["data"] == {CONF_TADO_ENTRY_ID: source.entry_id}
    assert result["result"].unique_id == source.entry_id
    source.runtime_data._tado.get_zone_states.assert_called_once_with()
    source.runtime_data._tado.set_zone_overlay.assert_not_called()
    setup_entry.assert_called_once()


async def test_duplicate(hass, source, setup_entry):
    MockConfigEntry(
        domain=DOMAIN, unique_id=source.entry_id, data={CONF_TADO_ENTRY_ID: source.entry_id}
    ).add_to_hass(hass)
    result = await start(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_TADO_ENTRY_ID: source.entry_id}
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"
    source.runtime_data._tado.get_zone_states.assert_not_called()
    setup_entry.assert_not_called()


@pytest.mark.parametrize("failure", ["cannot_read", "unsupported_response", "incompatible_source"])
async def test_error_recovery(hass, source, setup_entry, failure):
    client = source.runtime_data._tado
    if failure == "cannot_read":
        client.get_zone_states.side_effect = RuntimeError("private vendor detail")
    elif failure == "unsupported_response":
        client.get_zone_states.return_value = {}
    else:
        source.runtime_data = None
    result = await start(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_TADO_ENTRY_ID: source.entry_id}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": failure}
    client.get_zone_states.side_effect = None
    client.get_zone_states.return_value = RAW
    source.runtime_data = SimpleNamespace(_tado=client)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_TADO_ENTRY_ID: source.entry_id}
    )
    await hass.async_block_till_done()
    assert result["type"] is FlowResultType.CREATE_ENTRY
    client.set_zone_overlay.assert_not_called()


async def test_selection_removed_recovery(hass, source, setup_entry):
    other = MockConfigEntry(domain="tado", title="Other home", data={})
    other.add_to_hass(hass)
    other.runtime_data = source.runtime_data
    other._async_set_state(hass, ConfigEntryState.LOADED, None)
    result = await start(hass)
    source._async_set_state(hass, ConfigEntryState.NOT_LOADED, None)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_TADO_ENTRY_ID: source.entry_id}
    )
    assert result["errors"] == {"base": "source_unavailable"}
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_TADO_ENTRY_ID: other.entry_id}
    )
    await hass.async_block_till_done()
    assert result["type"] is FlowResultType.CREATE_ENTRY


async def test_last_source_unloads(hass, source):
    result = await start(hass)
    source._async_set_state(hass, ConfigEntryState.NOT_LOADED, None)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_TADO_ENTRY_ID: source.entry_id}
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "no_tado"
