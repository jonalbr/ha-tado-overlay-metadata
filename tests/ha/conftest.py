"""Fixtures using Home Assistant with a mocked Tado network boundary."""

from types import SimpleNamespace
from unittest.mock import Mock

import pytest

pytest.importorskip("homeassistant")

from homeassistant.config_entries import ConfigEntryState
from pytest_homeassistant_custom_component.common import MockConfigEntry

RAW = {"zoneStates": {"1": {"setting": {"type": "HEATING"}, "overlay": None}}}


@pytest.fixture(autouse=True)
def custom_integrations(enable_custom_integrations):
    """Enable loading the repository's custom component."""


@pytest.fixture
def source(hass):
    """Provide a loaded Tado config entry with a mocked network boundary."""
    entry = MockConfigEntry(domain="tado", title="Tado home", data={})
    entry.add_to_hass(hass)
    entry.runtime_data = SimpleNamespace(
        _tado=Mock(get_zone_states=Mock(return_value=RAW), set_zone_overlay=Mock())
    )
    entry._async_set_state(hass, ConfigEntryState.LOADED, None)
    return entry
