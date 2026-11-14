# Home Assistant developer guidance review

Reviewed on 2026-09-06 against the blog archive, including the September 2 entry,
and Core 2026.9.0. This is a scoped review, not a guarantee against future changes.

| Guidance | Result |
| --- | --- |
| [Modbus accessor deprecation, September 2](https://developers.home-assistant.io/blog/2026/09/02/modbus-get-hub-deprecation/) | No Modbus code. |
| [Configurator deprecation, August 31](https://developers.home-assistant.io/blog/2026/08/31/deprecate-configurator/) | Uses config flows, not Configurator. |
| Device registry changes, July and August 2026 | No device registry mutations, shared devices or helper device linking. |
| [Advanced mode removal](https://developers.home-assistant.io/blog/2026/05/26/advanced-mode-config-flow-deprecation/) | No advanced-mode flags. |
| [Duplicate config-entry reloads](https://developers.home-assistant.io/blog/2026/05/07/config-entry-listener-together-with-reloading-methods/) | No reload listener combined with flow reload methods. |
| [Local brand images](https://developers.home-assistant.io/blog/2026/02/24/brands-proxy-api/) | SVG source and PNG exports in the component's `brand/` directory. |
| [Config entry runtime data](https://developers.home-assistant.io/blog/2024/04/30/store-runtime-data-inside-config-entry/) | Typed `entry.runtime_data`, not a global `hass.data` map. |
| [Translated exceptions](https://developers.home-assistant.io/blog/2024/03/15/exception-translations/) | Action errors use English exception translation keys. |
| [Action registration](https://developers.home-assistant.io/docs/dev_101_services/) | Response-only action registered in `async_setup`, remaining registered after unload. |

Synchronous cloud reads run in HA's executor. The runtime has no blocking file
reads, deprecated job helpers, script engine, templates, custom frontend or polling.
The action and config flow use the current supported APIs for those responsibilities.

Additional guidance checked on 2026-11-14 for Home Assistant 2026.11.1:

| Guidance | Result |
| --- | --- |
| [Marketplace metadata](https://contributors.home-assistant.io/marketplace/reference/hacs-json/) | Retain `hacs.json` and `hacs/action`; both still serve Marketplace installations and catalog review. |
| [Integration categories](https://contributors.home-assistant.io/blog/2026/10/20/integration-categories/) | Declare `climate.thermostats_heating` for catalog discovery. |
| [Config-entry methods returning None](https://contributors.home-assistant.io/blog/2026/10/23/config-entry-methods-return-none/) | Boolean returns remain supported for custom integrations without deprecation. Retain them for compatibility with 2026.9.0. Setup failures already raise the appropriate exceptions. |

## Remaining compatibility dependency

The source Tado integration exposes no public action for full overlay expiry.
This adapter therefore uses `source.runtime_data._tado.get_zone_states()`.
That private dependency is version-sensitive even though the surrounding HA APIs
use current conventions. It is checked at runtime and covered with boundary
tests. An official replacement should supersede it when available.

Tests use synthetic data and lightweight HA doubles. Remote HACS/hassfest checks
and live verification of actual next-time-block expiry data are separate checks.
