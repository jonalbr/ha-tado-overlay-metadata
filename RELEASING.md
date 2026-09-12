# Release procedure

## Version and package

1. Choose the version.
2. Set the same version in `custom_components/tado_overlay_metadata/manifest.json`
   and `pyproject.toml`, run `uv lock`, and update `CHANGELOG.md`.
3. Run all [development checks](DEVELOPMENT.md#environment-and-checks), including
   the Linux Home Assistant suite with 100% config-flow branch coverage.
4. Run `uv run python scripts/build_release.py`. Inspect the ZIP under `dist/`;
   it contains integration files for extraction into
   `custom_components/tado_overlay_metadata/`. HACS downloads repository files.

## Publication

1. Confirm GitHub Actions tests, HACS validation and hassfest succeed on that commit.
2. Set the changelog release date and ensure the release commit includes it.
3. Create a tag matching the manifest, for example `v0.1.2`, and publish its GitHub
   release with changelog notes and the validated ZIP.

Use a prerelease if required live validation is incomplete. Repository description
and topics should identify Home Assistant, HACS and Tado. HACS publication uses
`jonalbr/ha-tado-overlay-metadata`.

Users install updates through HACS and restart Home Assistant. Release notes must
describe any migration requirements or changes to supported Home Assistant versions.
