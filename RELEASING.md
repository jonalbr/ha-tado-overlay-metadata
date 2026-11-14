# Release procedure

## Version and package

1. Choose the version.
2. Set the same version in `custom_components/tado_overlay_metadata/manifest.json`
   and `pyproject.toml`, run `uv lock`, and update `CHANGELOG.md`.
3. Run all [development checks](DEVELOPMENT.md#environment-and-checks), including
   the Linux Home Assistant suite with 100% config-flow branch coverage.
4. Run `uv run python scripts/build_release.py`. Inspect the ZIP under `dist/`;
   it contains integration files for extraction into
   `custom_components/tado_overlay_metadata/`. Marketplace downloads repository files.

## Automated publication

1. Complete the candidate's live Home Assistant smoke test. Use a manually
   published prerelease if required live validation is incomplete; the automated
   workflow publishes stable releases only.
2. Set the changelog release date, commit the version, lockfile and notes, and
   push the commit. Confirm all four jobs in the **Validate** workflow succeed.
3. Create and push an annotated tag matching the manifest and project version:

   ```console
   git tag -a v0.1.4 -m "Release 0.1.4"
   git push origin v0.1.4
   ```

Pushing a `v*` tag starts the **Release** workflow. It reuses all four validation
jobs, then builds the deterministic integration ZIP and publishes a stable GitHub
release with that ZIP and the matching dated section of `CHANGELOG.md`. A tag
that differs from the source version or lacks release notes fails before
publication. Existing releases are never overwritten. Version bumps and live
smoke tests remain manual.

Confirm the workflow succeeds and inspect the published notes and ZIP. Only the
publishing job has repository write permission; it uses GitHub's built-in token,
so no additional release secret is needed.

Repository description and topics should identify Home Assistant, Marketplace and Tado. Marketplace
uses `jonalbr/ha-tado-overlay-metadata`. Keep the `hacs.json` filename and
the HACS validation action as Marketplace uses the same metadata and catalog.
See the [Marketplace contributor documentation](https://contributors.home-assistant.io/marketplace/).

Users on Home Assistant 2026.11 or later install Marketplace updates from
**Settings > Updates** and restart Home Assistant. Users on earlier
versions update through HACS and restart. Release notes must
describe any migration requirements or changes to supported Home Assistant versions.
