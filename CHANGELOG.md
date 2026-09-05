# Changelog

## 0.1.1 — Unreleased

- Add explicit `restore_timed_off` for preserving finite OFF overlays in restore automations.
- Verify live capture and next-time-block expiry on HA 2026.9.0.
- Keep window decisions and persistence in the caller; no automatic controls added.

## 0.1.0 — Unreleased

- Add an English config flow linked to an existing built-in Tado connection.
- Add the read-only `capture` action with filtered or all-zone response data.
- Preserve absolute override expiry and distinguish manual OFF from schedule OFF.
- Reject missing expiry, unsupported types and malformed data explicitly.
- Handle source reloads without storing credentials or a second cloud session.
- Add HACS layout, local brand assets, uv-managed tests and release checks.
- Live Home Assistant and real next-time-block expiry validation are pending.
