# Bronze quality assessment

Version 0.1.2 is aligned with the applicable Bronze requirements in the
[Home Assistant quality scale](https://developers.home-assistant.io/docs/core/integration-quality-scale/).
This is a self-assessment of a custom integration. Home Assistant assigns custom
integrations the Custom designation; no official Bronze certification is claimed.

The assessment follows the [Bronze rules](https://developers.home-assistant.io/docs/core/integration-quality-scale/rules/)
available on 2026-09-12. Machine-readable status is recorded in
[`quality_scale.yaml`](../custom_components/tado_overlay_metadata/quality_scale.yaml).

| Rule | Status | Evidence |
| --- | --- | --- |
| `action-setup` | Done | Both response-only actions are registered in async_setup and remain registered after unload. |
| `appropriate-polling` | Exempt | No scheduled polling. Reads occur during configuration, startup and explicit capture calls. |
| `brands` | Done | Custom integration branding is provided by brand/icon.png and brand/icon@2x.png. |
| `common-modules` | Done | Shared source access and validation are in adapter.py; identifiers are in const.py. |
| `config-flow-test-coverage` | Done | Real Home Assistant flow-manager tests cover all statements and branches, error recovery and duplicates. CI enforces 100% coverage. |
| `config-flow` | Done | The UI selects a loaded built-in Tado entry. YAML configuration is not required. |
| `dependency-transparency` | Done | README documents the built-in Tado dependency, private coordinator interface and python-tado library. The manifest declares tado and no extra requirements. |
| `docs-actions` | Done | README documents capture and restore_timed_off parameters, responses, errors and examples. |
| `docs-triggers` | Exempt | No custom triggers are provided. |
| `docs-conditions` | Exempt | No custom conditions are provided. |
| `docs-high-level-description` | Done | README describes preserving classic Tado heating overlays for restoration automations. |
| `docs-installation-instructions` | Done | README includes prerequisites, HACS and manual installation, and UI setup. |
| `docs-removal-instructions` | Done | README explains entry deletion, file removal, restart and externally stored state. |
| `entity-event-setup` | Exempt | The integration creates no entities or entity event subscriptions. |
| `entity-unique-id` | Exempt | The integration creates no entities. |
| `has-entity-name` | Exempt | The integration creates no entities. |
| `runtime-data` | Done | Typed ConfigEntry.runtime_data holds Runtime with a lock and an active flag. |
| `test-before-configure` | Done | The flow checks the source client contract and performs a read-only get_zone_states call before creating an entry. |
| `test-before-setup` | Done | Startup validates the source and response envelope before assigning runtime data. Temporary failures use ConfigEntryNotReady. |
| `unique-config-entry` | Done | The source Tado entry ID is the unique ID. Duplicate entries are rejected before a network request. |

## Verification

- 61 portable tests cover normalization, action boundaries, serialization and timed OFF.
- 17 tests use Home Assistant 2026.9.2 and mocked Tado network calls to check flow
  creation, failures, recovery, duplicates, source reloads and the action lifecycle.
- Config-flow coverage is 100% for statements and branches. The CI job fails below 100%.
- The local release validator checks version agreement, translations, required
  files and both icon sizes. The release builder checks ZIP integrity.

The [branding rule](https://developers.home-assistant.io/docs/core/integration-quality-scale/rules/brands/)
is satisfied using the supported
[local branding mechanism for custom integrations](https://developers.home-assistant.io/blog/2026/02/24/brands-proxy-api/).
The original assets are bundled with the component rather than submitted to the
central brands repository used by core integrations.

This assessment does not claim Silver, full runtime coverage, or compatibility
with all future Home Assistant versions. The private Tado interface remains a
maintenance dependency. A release requires the candidate's live smoke test and
successful HACS/hassfest validation under the [release procedure](../RELEASING.md).
