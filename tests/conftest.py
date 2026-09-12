"""Minimal HA boundary doubles for portable unit tests; no live HA is implied."""

import importlib.util
import sys
from enum import Enum
from pathlib import Path
from types import ModuleType, SimpleNamespace

import pytest

COMPONENT = Path(__file__).parents[1] / "custom_components/tado_overlay_metadata"


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def snapshot():
    return load_module("unit_snapshot", COMPONENT / "snapshot.py")


@pytest.fixture
def ha_boundary(monkeypatch):
    for name in list(sys.modules):
        if name == "unit_tado_metadata" or name.startswith("unit_tado_metadata."):
            monkeypatch.delitem(sys.modules, name)

    class ConfigEntryState(Enum):
        LOADED = "loaded"
        NOT_LOADED = "not_loaded"

    class HomeAssistantError(Exception):
        def __init__(self, message=None, *, translation_domain=None, translation_key=None):
            self.translation_key = translation_key
            super().__init__(message or translation_key)

    class ConfigFlow:
        def __init_subclass__(cls, **kwargs):
            pass

        async def async_set_unique_id(self, value):
            self.unique_id = value

        def _abort_if_unique_id_configured(self):
            if self.unique_id in getattr(self, "configured_ids", set()):
                raise HomeAssistantError("already_configured")

        def async_abort(self, **kwargs):
            return {"type": "abort", **kwargs}

        def async_show_form(self, **kwargs):
            return {"type": "form", **kwargs}

        def async_create_entry(self, **kwargs):
            return {"type": "create_entry", **kwargs}

    exports = {
        "homeassistant": {},
        "homeassistant.config_entries": {
            "ConfigEntry": object,
            "ConfigEntryState": ConfigEntryState,
            "ConfigFlow": ConfigFlow,
            "ConfigFlowResult": dict,
        },
        "homeassistant.core": {
            "HomeAssistant": object,
            "ServiceCall": object,
            "SupportsResponse": SimpleNamespace(ONLY="only"),
        },
        "homeassistant.exceptions": {
            "ConfigEntryError": HomeAssistantError,
            "ConfigEntryNotReady": HomeAssistantError,
            "HomeAssistantError": HomeAssistantError,
            "ServiceValidationError": HomeAssistantError,
        },
        "homeassistant.helpers": {},
        "homeassistant.helpers.config_validation": {
            "config_entry_only_config_schema": lambda domain: None,
        },
        "homeassistant.helpers.typing": {"ConfigType": dict},
    }
    for name, members in exports.items():
        module = ModuleType(name)
        module.__dict__.update(members)
        monkeypatch.setitem(sys.modules, name, module)
    # Do not overwrite a real custom_components namespace.
    module = load_module("unit_tado_metadata", COMPONENT / "__init__.py")
    flow = load_module("unit_tado_metadata.config_flow", COMPONENT / "config_flow.py")
    entries = {}
    service = {}

    def register(domain, name, handler, **kwargs):
        service.update(handler=handler, domain=domain, name=name, **kwargs)

    async def executor(fn):
        return fn()

    hass = SimpleNamespace(
        data={},
        config_entries=SimpleNamespace(
            async_get_entry=entries.get,
            async_entries=lambda domain: [e for e in entries.values() if e.domain == domain],
        ),
        services=SimpleNamespace(async_register=register),
        async_add_executor_job=executor,
    )
    return SimpleNamespace(
        module=module,
        flow=flow,
        hass=hass,
        entries=entries,
        service=service,
        states=ConfigEntryState,
        error=HomeAssistantError,
    )
