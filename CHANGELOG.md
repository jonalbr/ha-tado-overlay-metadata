# Changelog

## 0.1.2 - Unreleased

- Validate the existing Tado API connection during configuration and startup.
- Retry startup after temporary connection failures and report missing or incompatible sources.
- Add Home Assistant framework tests with full config-flow coverage and error recovery checks.
- Document both actions, installation, removal, dependencies and restoration behavior.
- Add a Bronze quality self-assessment and disclose AI-assisted development.

## 0.1.1 - 2026-09-06

- Add `restore_timed_off` to preserve finite OFF overlays in restoration automations.

## 0.1.0 - Initial implementation

- Add an English config flow linked to an existing built-in Tado connection.
- Add the read-only `capture` action with filtered or all-zone response data.
- Preserve absolute override expiry and distinguish manual OFF from schedule OFF.
- Reject missing expiry, unsupported types and malformed data.
- Resolve the current Tado session on each action to support source reloads.
- Add HACS metadata, local brand assets, tests and release checks.
