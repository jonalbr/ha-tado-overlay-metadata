"""Fixtures using Home Assistant with a mocked Tado network boundary."""

from unittest.mock import create_autospec, patch

import pytest

pytest.importorskip("homeassistant")

from homeassistant.components.tado.const import CONF_REFRESH_TOKEN
from homeassistant.components.tado.coordinator import TadoDataUpdateCoordinator
from homeassistant.config_entries import ConfigEntryState
from PyTado.interface import Tado
from PyTado.interface.api import Tado as ClassicTado
from pytest_homeassistant_custom_component.common import MockConfigEntry

RAW = {"zoneStates": {"1": {"setting": {"type": "HEATING"}, "overlay": None}}}


@pytest.fixture(autouse=True)
def custom_integrations(enable_custom_integrations):
    """Enable loading the repository's custom component."""


@pytest.fixture
def source(hass):
    """Provide a loaded Tado config entry with a mocked network boundary."""
    entry = MockConfigEntry(
        domain="tado", title="Tado home", data={CONF_REFRESH_TOKEN: "test-token"}
    )
    entry.add_to_hass(hass)
    # Tado delegates snake_case methods to the selected API after authentication.
    # Keep that real delegation while replacing transport and the classic API.
    with patch("PyTado.interface.interface.Http"):
        client = Tado()
    client._api = create_autospec(ClassicTado, instance=True)
    client.get_zone_states.return_value = RAW
    entry.runtime_data = TadoDataUpdateCoordinator(hass, entry, client)
    entry._async_set_state(hass, ConfigEntryState.LOADED, None)
    return entry
