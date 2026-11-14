# Development

## Environment and checks

The development environment uses Python 3.14 and
[uv](https://docs.astral.sh/uv/).

Portable parser, action-boundary and lifecycle tests:

```console
uv sync --locked
uv run pytest --ignore=tests/ha
uv run ruff check .
uv run ruff format --check .
uv run python scripts/check_release.py
uv run python scripts/build_release.py
```

Home Assistant tests require Linux. Run the following commands in a Linux
terminal, including a WSL terminal on Windows:

```console
uv sync --locked --group ha-test
uv run --group ha-test pytest tests/ha -o asyncio_mode=auto -o asyncio_default_fixture_loop_scope=function --cov=custom_components/tado_overlay_metadata --cov-branch --cov-report=term-missing --cov-fail-under=100
```

On Windows, run the portable suite above directly in PowerShell. The `ha-test`
dependencies have Linux platform markers: `uv sync --all-groups --locked` and
`--group ha-test` do not install Home Assistant into the Windows environment.

To run the framework suite from PowerShell at the repository root, use an
installed Ubuntu WSL distribution (with uv available inside WSL):

```powershell
wsl --distribution Ubuntu --cd (Get-Location).Path -- bash -lc `
  'UV_PROJECT_ENVIRONMENT=/tmp/ha-tado-overlay-metadata-tests uvx --from uv==0.13.8 uv run --locked --group ha-test pytest tests/ha -o asyncio_mode=auto -o asyncio_default_fixture_loop_scope=function --cov=custom_components/tado_overlay_metadata --cov-branch --cov-report=term-missing --cov-fail-under=100'
```

This command creates or synchronizes a separate Linux virtual environment and
leaves the Windows `.venv` in place. WSL may clear `/tmp` when it stops; the next
run recreates the environment using uv's download cache. No Windows environment
activation is needed for this command.

The pytest configuration disables respx's separate plugin so Home Assistant can
install its httpx alias first. The HA fixtures still use respx for HTTP mocking.
Custom integrations are enabled by default by the new `hass` fixture. See the
[official test-package guide](https://github.com/home-assistant/core/blob/2026.11.1/packages/pytest-homeassistant/README.md).

Coverage measures the component directory by filesystem path. Using a dotted
module name would import Home Assistant before its pytest bootstrap and create
inconsistent loader classes.

GitHub Actions runs the portable suite, framework suite, Ruff, release checks,
Marketplace catalog validation (using `hacs/action`) and hassfest.

## Branding

`custom_components/tado_overlay_metadata/brand/icon.svg` is the editable source.
It combines the white [Simple Icons Tado wordmark](https://github.com/simple-icons/simple-icons/blob/develop/icons/tado.svg)
with an stacked-layer symbol on `#FFA900`. The wordmark is sourced
from Simple Icons under [CC0](https://github.com/simple-icons/simple-icons/blob/develop/LICENSE.md).

Home Assistant's local brand-image API requires PNG files. Export the SVG to
`icon.png` (256 px) and `icon@2x.png` (512 px) from a Linux/WSL terminal with Cairo
installed:

```console
uv run scripts/render_brand.py
```

The script declares its own pinned rendering dependency; it is not a runtime or
test dependency. Commit the SVG and both PNG exports together.

## Architecture

- `adapter.py` resolves the current built-in Tado client and validates its API.
- `config_flow.py` selects an existing source and validates it before saving its ID.
- `__init__.py` registers actions and manages per-entry runtime and serialization.
- `snapshot.py` normalizes cloud payloads without Home Assistant or network dependencies.
- `const.py` contains shared integration identifiers.

The adapter uses `source.runtime_data._tado.get_zone_states()` and
`set_zone_overlay()`. Source clients are resolved for each action to support Tado
reloads. Synchronous API calls run in Home Assistant's executor. Configuration and
startup validate a read without sending heating commands; snapshots are discarded.
Per-zone errors do not invalidate the response envelope during setup.

Transient startup failures raise `ConfigEntryNotReady`. Missing sources and
incompatible API contracts raise `ConfigEntryError`. Authentication remains with
the built-in Tado entry. Vendor exception text is excluded from integration errors
because it can contain sensitive request details.

Actions are registered in `async_setup` and stay registered after entries unload.
Typed `ConfigEntry.runtime_data` holds a lock and an active flag. Waiting actions
recheck the runtime after acquiring the lock. Unloading cannot revoke a cloud
command already in flight.

## Documentation

Keep release commands in `RELEASING.md`, technical rationale here, and user instructions
in `README.md`. Changelog entries describe changes to the product rather than development sessions.
Update English translations and `strings.json` together.

## Compatibility validation

Check the private Tado client contract when changing the supported Home Assistant
version. Framework fixtures construct Core's real Tado coordinator with the
real python-tado interface and an autospecced classic API. Contract tests verify
Core's required library version and the timed-OFF call signature. Automated tests mock network responses;
the live installation and cloud behavior checklist is in `RELEASING.md`.
