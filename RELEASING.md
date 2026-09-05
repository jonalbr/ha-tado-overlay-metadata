# Releasing

Repository: `jonalbr/ha-tado-overlay-metadata` (public GitHub).
Repository metadata must include a short description and topics such as
`home-assistant`, `hacs`, `tado`, and `custom-integration`.

## Local checks

1. Use `uv sync --locked` and run the tests, Ruff lint/format checks and
   `uv run python scripts/check_release.py`.
2. Update the version in both `manifest.json` and `pyproject.toml`, regenerate
   `uv.lock` with `uv lock`, and document the change in `CHANGELOG.md`.
3. Run `uv run python scripts/build_release.py`. The generated ZIP contains only
   the integration directory contents, suitable for extraction into
   `custom_components/tado_overlay_metadata/`. HACS itself downloads repository files.

## Live smoke test checklist

- Install via HACS on a test HA instance, restart, then add the config entry.
- Verify the English config flow; reject duplicate entries for the same source.
- Call `capture` with a known zone and with no filter. Check the action response.
- Verify auto, indefinite manual heat/off, and a real next-time-block override.
- Confirm the original absolute expiry is available and does not move on repeat reads.
- Confirm a source Tado reload is followed automatically by the next call.
- Unload/delete the metadata entry; a subsequent action must fail clearly.
- Check logs for errors. Setup and `capture` must not send heating or presence commands.
- Explicitly test `restore_timed_off`, verify OFF and a stable future expiry with two reads, then restore the prior setting. No presence command is allowed.

These tests do not require changing a production household's temperatures solely
to populate fixtures. Validate observed existing states or use a separate test setup.
Never publish live diagnostics or credentials as test fixtures.

## GitHub release

Review the committed files for private data, push the tested commit and inspect
the GitHub Actions results. Publish a tag matching the manifest version, for
example `v0.1.0`. Mark development releases as prereleases until live verification
has passed. Normal users should install only a release whose limitations they accept.

GitHub Actions contains local tests and repository checks plus HACS validation
and Home Assistant's hassfest check. Those remote validators have not run until
the repository is pushed; local checks must not be described as those checks passing.

Gitea may hold a development copy or mirror, but HACS reads the public GitHub copy.

## Verification recorded for 0.1.1

- HACS installation and HA restart/config entry loading on Core 2026.9.0.
- All-zone and filtered `capture`, indefinite manual OFF and a next-time-block
  setting returned as TIMER with an absolute expiry.
- Explicit timed OFF returned a stable expiry on two fresh reads (one second
  earlier than requested because the relative duration uses whole seconds).
- Original manual OFF restored after each controlled low-temperature/OFF test.
- 61 portable unit tests and GitHub HACS/hassfest validation passed.

The checklist above remains useful for future releases. This records the cases
actually observed; it does not claim a full test matrix on all Tado accounts,
device types or future Home Assistant versions.
