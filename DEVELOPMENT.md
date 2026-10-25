# Development

## Environment and checks

The development environment uses Python 3.14.2 or later and
[uv](https://docs.astral.sh/uv/). `.python-version` selects Python 3.14.9; `uv.lock`
pins the development packages.

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
uv run --group ha-test pytest tests/ha -o asyncio_mode=auto --cov=custom_components.tado_overlay_metadata.config_flow --cov-branch --cov-report=term-missing --cov-fail-under=100
```

On Windows, run the portable suite above directly in PowerShell. The `ha-test`
dependencies have Linux platform markers: `uv sync --all-groups --locked` and
`--group ha-test` do not install Home Assistant into the Windows environment.

To run the framework suite from PowerShell at the repository root, use a
installed Ubuntu WSL distribution (with uv available inside WSL):

```powershell
wsl --distribution Ubuntu --cd (Get-Location).Path -- bash -lc `
  'UV_PROJECT_ENVIRONMENT=/tmp/ha-tado-overlay-metadata-tests uvx --from uv==0.13.5 uv run --locked --group ha-test pytest tests/ha -o asyncio_mode=auto --cov=custom_components.tado_overlay_metadata.config_flow --cov-branch --cov-report=term-missing --cov-fail-under=100'
```

This command creates or synchronizes a separate Linux virtual environment and
leaves the Windows `.venv` in place. WSL may clear `/tmp` when it stops; the next
run recreates the environment using uv's download cache. No Windows environment
activation is needed for this command.

GitHub Actions runs the portable suite, framework suite, Ruff, release checks,
HACS validation and hassfest.

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
