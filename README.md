# Tado Overlay Metadata

Tado Overlay Metadata is a Home Assistant custom integration for automations that
temporarily pause heating and need to preserve the original Tado settings and
expiry time. It uses the built-in Tado integration's authenticated connection.
AI tools were used to assist with the code, tests and documentation in this
project.

Two actions are available:

- `capture` reads heating modes, setpoints, overlay termination types and absolute
  expiry times. Invalid or unsupported zones are reported individually.
- `restore_timed_off` restores a finite OFF overlay until its saved deadline.

The integration creates no entities, triggers or conditions. Automations are
responsible for deciding when to pause or resume heating and for storing snapshots.
It does not manage windows, change Home/Away settings or replace the built-in
Tado integration.

## Requirements and compatibility

- Home Assistant **2026.9.0 or later**, with the built-in **Tado** integration
  configured and loaded. Authentication is managed by that integration.
- Classic Tado heating zones. Tado X and air-conditioning zones are unsupported.
- Internet access to the Tado cloud. Reads and writes consume the account's API
  quota, including validation reads during configuration and startup.

This integration relies on the built-in Tado coordinator's private `_tado` client
and the `python-tado` library installed by Home Assistant. It installs no additional
runtime packages. Changes to that private interface may require an integration
update.

Finite overlays require an absolute `expiry` or `projectedExpiry` supplied by Tado.
Missing deadlines are reported as errors; remaining times are never inferred from
the capture time. A next-time-block setting may be returned by Tado as `TIMER`.

## Installation

### HACS

[![Open this repository in HACS](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=jonalbr&repository=ha-tado-overlay-metadata&category=integration)

1. In HACS, open **Custom repositories**.
2. Add `https://github.com/jonalbr/ha-tado-overlay-metadata` with category **Integration**.
3. Download **Tado Overlay Metadata** and restart Home Assistant.
4. Open **Settings > Devices & services > Add integration**.
5. Select **Tado Overlay Metadata**, then select the existing Tado connection.

### Manual installation

1. Copy the `custom_components/tado_overlay_metadata` directory into the Home
   Assistant configuration directory's `custom_components` folder.
2. Restart Home Assistant.
3. Follow steps 4 and 5 above. No YAML configuration is required.

## Actions

Both actions return response data and require a `response_variable` in a script
or automation. With multiple loaded metadata entries, supply `config_entry_id` to
select the **Tado Overlay Metadata** entry, rather than the built-in Tado entry.
The action editor provides an integration selector for this field.

### Capture overlay metadata

```yaml
sequence:
  - action: tado_overlay_metadata.capture
    data:
      zone_ids: [1, 2]
    response_variable: metadata
```

| Parameter | Required | Description |
| --- | --- | --- |
| `config_entry_id` | With multiple loaded metadata entries | Metadata entry to use |
| `zone_ids` | No | List of 1–100 positive integer Tado zone IDs; omitted means all zones |

The IDs in the example must be replaced with the account's Tado zone IDs. A capture
without a filter returns these IDs as keys in `snapshots` and `errors`. Every call
makes one all-zone cloud request; filtering only limits the returned data. There
is no background polling or response cache.

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

| Snapshot field | Meaning |
| --- | --- |
| `version` | Snapshot schema version, currently `1` |
| `mode` | `auto`, `heat` or `off` |
| `temperature` | Celsius setpoint for a heating overlay; otherwise `null` |
| `termination` | `SCHEDULE`, `MANUAL`, `TADO_MODE`, `NEXT_TIME_BLOCK` or `TIMER` |
| `expires_at` | Absolute UTC Unix timestamp in seconds; `null` for schedule or indefinite manual overlays |

`auto` means no manual overlay, including when the schedule calls for heating to
be off. An explicit manual OFF overlay is returned as `off`. `captured_at` records
local request completion, not the time a thermostat last communicated with Tado.

Whole-request failures raise an action error. Per-zone failures appear in `errors`
and have no corresponding snapshot. They include missing or invalid expiry,
unsupported zone or termination types, invalid temperatures and malformed data.

### Restore timed OFF

This action writes an OFF timer using the remaining time until the supplied
deadline. It supports finite OFF overlays that `climate.turn_off` cannot preserve.

| Parameter | Required | Description |
| --- | --- | --- |
| `config_entry_id` | With multiple loaded metadata entries | Metadata entry to use |
| `zone_id` | Yes | Positive integer Tado heating zone ID |
| `expires_at` | Yes | Saved absolute UTC Unix timestamp, in whole seconds and still in the future |

The following script fragment assumes `saved_snapshot` and `saved_zone_id` have
been loaded from persistent storage and the automation has already checked that
restoration is allowed:

```yaml
- condition: template
  value_template: >-
    {{ saved_snapshot.mode == 'off'
       and saved_snapshot.expires_at is number
       and saved_snapshot.expires_at > as_timestamp(now()) }}
- action: tado_overlay_metadata.restore_timed_off
  data:
    zone_id: "{{ saved_zone_id | int }}"
    expires_at: "{{ saved_snapshot.expires_at | int }}"
  response_variable: restored
```

The response contains `zone_id` and `requested_expires_at`. It acknowledges the
requested write, not delivery to the thermostat. Expired input, including less
than one whole second remaining, raises an action error without sending a command.
The action does not check windows or heating-season conditions.

## Restoration workflows

1. Capture the required zones and check each zone for errors.
2. Persist each original snapshot before changing heating. Keep it separate from
   the temporary OFF state.
3. Immediately before restoring, check the current conditions that govern heating.
4. For a finite overlay, compare its saved deadline to the current time. If the
   deadline has passed, return to the current schedule when conditions permit.
   Otherwise restore only the remaining duration. Use `restore_timed_off` for OFF.

Missing metadata must not trigger restoration. A new next-time-block command can
extend an expired override beyond its original deadline and must not substitute
for the saved expiry.

Tado accepts relative timer durations, so transport latency can shift the server
deadline by a few seconds. After an uncertain write result, read back with `capture`
before retrying. An offline thermostat may not have received a successful write.

## Privacy and limitations

The integration stores only its link to a Tado config entry. It does not persist
heating snapshots, credentials or raw cloud responses. Action responses exclude
account profiles, room names, tokens and device serial numbers. Authentication
refresh and underlying library logging are managed by Home Assistant and Tado.

Calls through one metadata entry are serialized. The built-in integration, other
clients and manual commands operate independently. Capture and a later heating
command are separate operations, and cloud data may reflect an older device report.

## Removal

1. Disable or update automations that call this integration's actions.
2. Open **Settings > Devices & services > Tado Overlay Metadata** and delete its entries.
3. Remove the integration from HACS, or delete its directory for a manual installation.
4. Restart Home Assistant.

Removal does not cancel an OFF timer already sent to Tado or remove snapshots
stored by an automation. Those remain managed by Tado and the calling automation.

## Development and AI assistance

AI tools were used to assist with the code, tests and documentation in this
project.

## License

[MIT](LICENSE). This is an independent community integration, not an official Tado product.
