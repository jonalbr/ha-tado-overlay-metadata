"""Timed OFF must never turn an expired finite overlay into indefinite OFF."""

from unittest.mock import Mock

import pytest


def test_timed_off_uses_remaining_duration_and_off(ha_boundary, monkeypatch):
    b = ha_boundary
    monkeypatch.setattr(b.module, "time", lambda: 1000.7)
    client = Mock()
    b.module.set_timed_off(client, 7, 1061)
    client.set_zone_overlay.assert_called_once_with(
        7, "TIMER", duration=60, device_type="HEATING", power="OFF"
    )


@pytest.mark.parametrize("deadline", [999, 1000, 1001])
def test_expired_or_subsecond_deadline_does_not_write(ha_boundary, monkeypatch, deadline):
    b = ha_boundary
    monkeypatch.setattr(b.module, "time", lambda: 1000.7)
    client = Mock()
    with pytest.raises(b.error, match="expiry_passed"):
        b.module.set_timed_off(client, 7, deadline)
    client.set_zone_overlay.assert_not_called()


@pytest.mark.parametrize("value", [True, 0, -1, 1.5, "1", None])
def test_timed_off_schema_rejects_invalid_deadline(ha_boundary, value):
    import voluptuous as vol

    with pytest.raises(vol.Invalid):
        ha_boundary.module.TIMED_OFF_SCHEMA({"zone_id": 7, "expires_at": value})
