# Tado Overlay Metadata

A small Home Assistant custom integration that reads original Tado heating
overlay settings and their absolute expiry times. Designed for automations that
temporarily pause heating and need to remember the previous settings.

**Status: initial development version.** Unit tests cover the parser, action
boundary, config flow and unload/reload behavior. Live capture succeeded on HA 2026.9.0, including a next-time-block setting returned by Tado as a TIMER with an absolute expiry. The timed-OFF action was also verified live: two reads returned the same finite OFF expiry; the original manual OFF state was then restored.

## What it does

- Uses an existing, loaded **built-in Tado integration**, without another login.
- Provides the response-only action `tado_overlay_metadata.capture`.
- Reads fresh cloud data on demand; no periodic polling is added.
- Returns heating mode, temperature, original termination type and absolute expiry.
- Reports malformed, unsupported or incomplete zones individually.

It also offers the explicit `restore_timed_off` action for the finite-OFF case the built-in climate action cannot preserve. It does not automatically manage windows, change Home/Away or persist snapshots. Those responsibilities belong to the calling automation.
It does not replace the built-in Tado integration.

## Compatibility

- Home Assistant **2026.9.0 or later**; source compatibility was reviewed against
  Core 2026.9.0 and `python-tado` 0.18.16. Later versions need verification.
- Classic Tado heating zones using the `zoneStates` API format. Tado X and
  air-conditioning zones are not currently supported.
- An internal adapter accesses the built-in coordinator's `_tado` client. This
  private dependency may need maintenance after a Home Assistant update.
- A valid absolute `expiry` or `projectedExpiry` is required for finite overlays.
  A live next-time-block setting was returned as a TIMER with a valid expiry; other account and device combinations still need verification. Missing expiry data produces an error rather than an invented time.

## Install with HACS

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=jonalbr&repository=ha-tado-overlay-metadata&category=integration)

The button opens HACS with this repository and the Integration category prefilled.
Confirm adding the repository, download it, then restart Home Assistant and add
**Tado Overlay Metadata** under **Settings → Devices & services**.

Alternatively, add it manually:

1. In HACS, open **Custom repositories**.
2. Add `https://github.com/jonalbr/ha-tado-overlay-metadata`, category **Integration**.
3. Download **Tado Overlay Metadata** and restart Home Assistant.
4. Open **Settings → Devices & services → Add integration**.
5. Select **Tado Overlay Metadata**, then your existing Tado connection.

For manual installation, copy `custom_components/tado_overlay_metadata` into
Home Assistant's `custom_components` directory and follow steps 3–5. No YAML
configuration is required. Do not copy the entire repository into that directory.

## Use from a script or automation

```yaml
sequence:
  - action: tado_overlay_metadata.capture
    data:
      zone_ids: [1, 2]
    response_variable: metadata
```

The IDs above are examples. Omit `zone_ids` to request all zones. Each call still
uses one all-zone request; filtering only limits the returned data.

If you configure multiple Tado accounts, specify the **metadata integration's**
`config_entry_id` in the action. This is not the source Tado config entry ID.

Example response:

```json
{
  "captured_at": "2026-09-06T10:00:00+00:00",
  "snapshots": {
    "1": {
      "version": 1,
      "mode": "heat",
      "temperature": 21.0,
      "termination": "TADO_MODE",
      "expires_at": 1788692400
    }
  },
  "errors": {"2": "missing_expiry"}
}
```

`expires_at` is a UTC Unix timestamp in seconds, not a remaining duration. The
`captured_at` field records when the local request completed; it is not proof of
when a thermostat last communicated with Tado.

| Field | Meaning |
| --- | --- |
| `version` | Snapshot schema version, currently `1` |
| `mode` | `auto`, `heat`, or `off` |
| `temperature` | Celsius setpoint for heating overlays; otherwise `null` |
| `termination` | `SCHEDULE`, `MANUAL`, `TADO_MODE`, `NEXT_TIME_BLOCK`, or `TIMER` |
| `expires_at` | Original absolute expiry, or `null` for schedule/indefinite manual |

`auto` means no manual overlay, including when the current schedule itself calls
for heating to be off. An explicit manual off overlay remains distinguishable.

## Use safely in a restore workflow

Check `errors` for every required zone, then **persist each snapshot before
changing heating**. Never overwrite that snapshot with the temporary off state.
On release, recheck the current window and heating-season conditions.

For finite settings, compare the original deadline to the current time. If it has
passed, return to the current Tado schedule. Otherwise only restore the remaining
duration. Do not send a fresh "next time block" command after the original deadline.
For a timer-based OFF overlay whose original deadline is still in the future,
call `tado_overlay_metadata.restore_timed_off` with `zone_id` and `expires_at`
from the saved snapshot, and a `response_variable`. It writes an OFF timer using
the remaining seconds. Check the release conditions immediately before calling.
Expired input raises an action error; the caller must recheck and return to
schedule when allowed. No Home/Away or schedule settings are changed.

Tado accepts relative timer durations, so transport latency can shift the server
deadline by a few seconds. A successful write response does not prove that an
offline thermostat has received it. Read back with `capture` after uncertain
results before retrying.

Missing metadata is not permission to resume heating. Whole-request failures
raise a Home Assistant action error; per-zone failures appear in `errors` and have
no matching snapshot. Unknown termination types are rejected.

## Privacy and limits

Only the normalized fields above leave this adapter. It does not store or export
tokens, account profiles, room names, device serials or raw cloud responses.
Underlying Tado/HA logging and authentication behavior remains their responsibility.
The existing authenticated Tado session performs the read, which consumes cloud
quota and may refresh authentication internally as usual.

Concurrent calls made through one metadata config entry are serialized. Other
clients, the built-in integration and user actions are independent; this action
is not an atomic transaction with a later heating command. HA being online also
does not guarantee that Tado's last device report is fresh.

## Development

Use [uv](https://docs.astral.sh/uv/):

```console
uv sync --locked
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv run python scripts/check_release.py
uv run python scripts/build_release.py
```

Python 3.14 and development dependencies are pinned through `.python-version`,
`pyproject.toml` and `uv.lock`. The runtime has no additional dependencies: it
uses Home Assistant and its existing Tado integration.

Tests use synthetic Tado payloads and minimal Home Assistant boundary doubles;
they do not substitute for a live integration test. See [RELEASING.md](RELEASING.md)
for the installation smoke test required before calling a version production-ready.

GitHub Actions only validates this repository. The HACS compatibility job does
not publish, submit or add the integration to the public HACS catalog. Installation
remains through this custom repository unless a separate catalog submission is made.

## Updates and removal

Publish a versioned GitHub release with a matching `manifest.json` version to make
updates selectable in HACS. Restart HA after installing an update. Keep the
domain `tado_overlay_metadata` unchanged across releases.

Before removing the integration, disable or update any automation that calls its
action. Remove its config entries, then remove the download in HACS and restart.
The integration itself holds no saved heating states or timers.

## License

MIT. This is an independent community integration, not an official Tado product.
