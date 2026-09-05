"""HA boundary unit tests: lifecycle, actions, errors and concurrent requests.

These test the integration code with minimal HA doubles, not HA's framework.
"""

import asyncio
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
import voluptuous as vol

RAW = {"zoneStates": {"1": {"setting": {"type": "HEATING"}, "overlay": None}}}


async def configured(boundary):
    metadata = SimpleNamespace(
        entry_id="metadata",
        domain="tado_overlay_metadata",
        data={"tado_entry_id": "source"},
        state=boundary.states.LOADED,
    )
    client = SimpleNamespace(get_zone_states=Mock(return_value=RAW))
    source = SimpleNamespace(
        entry_id="source",
        domain="tado",
        title="Tado",
        state=boundary.states.LOADED,
        runtime_data=SimpleNamespace(_tado=client),
    )
    boundary.entries.update(metadata=metadata, source=source)
    await boundary.module.async_setup(boundary.hass, {})
    await boundary.module.async_setup_entry(boundary.hass, metadata)
    return metadata, source, client


def test_setup_capture_unload(ha_boundary):
    async def run():
        b = ha_boundary
        metadata, source, client = await configured(b)
        client.get_zone_states.assert_not_called()
        result = await b.service["handler"](SimpleNamespace(data={}))
        assert result["snapshots"]["1"]["mode"] == "auto"
        assert result["errors"] == {}
        assert "captured_at" in result
        client.get_zone_states.assert_called_once_with()
        await b.module.async_unload_entry(b.hass, metadata)
        with pytest.raises(b.error):
            await b.service["handler"](SimpleNamespace(data={}))

    asyncio.run(run())


def test_source_reload_and_unavailability(ha_boundary):
    async def run():
        b = ha_boundary
        _, source, old_client = await configured(b)
        new_client = SimpleNamespace(get_zone_states=Mock(return_value=RAW))
        source.runtime_data = SimpleNamespace(_tado=new_client)
        await b.service["handler"](SimpleNamespace(data={}))
        old_client.get_zone_states.assert_not_called()
        new_client.get_zone_states.assert_called_once()
        source.state = b.states.NOT_LOADED
        with pytest.raises(b.error, match="source_not_loaded"):
            await b.service["handler"](SimpleNamespace(data={}))

    asyncio.run(run())


def test_exception_does_not_disclose_vendor_error(ha_boundary):
    async def run():
        b = ha_boundary
        _, _, client = await configured(b)
        client.get_zone_states.side_effect = RuntimeError("secret-session-information")
        with pytest.raises(b.error) as error:
            await b.service["handler"](SimpleNamespace(data={}))
        assert "secret" not in str(error.value)
        assert error.value.__suppress_context__

    asyncio.run(run())


def test_concurrent_requests_serialized(ha_boundary):
    async def run():
        b = ha_boundary
        await configured(b)
        running = 0
        maximum = 0

        async def executor(fn):
            nonlocal running, maximum
            running += 1
            maximum = max(maximum, running)
            await asyncio.sleep(0)
            result = fn()
            running -= 1
            return result

        b.hass.async_add_executor_job = executor
        await asyncio.gather(*(b.service["handler"](SimpleNamespace(data={})) for _ in range(3)))
        assert maximum == 1

    asyncio.run(run())


@pytest.mark.parametrize("value", [True, 0, -1, 1.5, "1", []])
def test_zone_schema_rejects_invalid_ids(ha_boundary, value):
    with pytest.raises(vol.Invalid):
        ha_boundary.module.CAPTURE_SCHEMA({"zone_ids": [value]})


def test_config_flow_no_tado_and_duplicate(ha_boundary):
    async def run():
        b = ha_boundary
        flow = b.flow.TadoOverlayMetadataFlow()
        flow.hass = b.hass
        assert (await flow.async_step_user())["reason"] == "no_tado"
        await configured(b)
        result = await flow.async_step_user()
        assert result["type"] == "form"
        result = await flow.async_step_user({"tado_entry_id": "source", "ignored": "not-stored"})
        assert result["data"] == {"tado_entry_id": "source"}
        flow.configured_ids = {"source"}
        with pytest.raises(b.error, match="already_configured"):
            await flow.async_step_user({"tado_entry_id": "source"})

    asyncio.run(run())
