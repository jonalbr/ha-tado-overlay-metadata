"""Choose an existing Tado connection without asking for credentials."""

from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigEntryState, ConfigFlow, ConfigFlowResult

from .const import CONF_TADO_ENTRY_ID, DOMAIN, NAME, SOURCE_DOMAIN


class TadoOverlayMetadataFlow(ConfigFlow, domain=DOMAIN):
    """One metadata entry per existing Tado account."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        choices = {
            entry.entry_id: entry.title
            for entry in self.hass.config_entries.async_entries(SOURCE_DOMAIN)
            if entry.state == ConfigEntryState.LOADED
        }
        if not choices:
            return self.async_abort(reason="no_tado")
        errors = {}
        if user_input is not None:
            selected = user_input.get(CONF_TADO_ENTRY_ID)
            if selected in choices:
                await self.async_set_unique_id(selected)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=f"{NAME}: {choices[selected]}",
                    data={CONF_TADO_ENTRY_ID: selected},
                )
            errors["base"] = "source_unavailable"
        return self.async_show_form(
            step_id="user",
            errors=errors,
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_TADO_ENTRY_ID, default=next(iter(choices))): vol.In(choices),
                }
            ),
        )
