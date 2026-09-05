"""Synthetic protocol tests, including malformed and expired overlays."""

import json

import pytest


def zone(kind="MANUAL", power="ON", expiry=None, temperature=21):
    termination = {"type": kind}
    if expiry is not None:
        termination["expiry"] = expiry
    return {
        "setting": {"type": "HEATING", "power": power},
        "overlay": {
            "setting": {"type": "HEATING", "power": power, "temperature": {"celsius": temperature}},
            "termination": termination,
        },
        "private_field": "do-not-export",
    }


def test_auto_even_when_schedule_is_off(snapshot):
    result = snapshot.normalize({"setting": {"type": "HEATING", "power": "OFF"}, "overlay": None})
    assert result["mode"] == "auto"
    assert result["termination"] == "SCHEDULE"


def test_manual_temperature(snapshot):
    assert snapshot.normalize(zone()) == {
        "version": 1,
        "mode": "heat",
        "temperature": 21,
        "termination": "MANUAL",
        "expires_at": None,
    }


def test_manual_off(snapshot):
    result = snapshot.normalize(zone(power="OFF", temperature=None))
    assert result["mode"] == "off"
    assert result["temperature"] is None


@pytest.mark.parametrize("kind", ["TIMER", "TADO_MODE", "NEXT_TIME_BLOCK"])
def test_absolute_deadline_preserved_even_in_past(snapshot, kind):
    result = snapshot.normalize(zone(kind, expiry="2020-01-01T00:00:00Z"))
    assert result["expires_at"] == 1577836800


def test_projected_expiry_and_timezone(snapshot):
    raw = zone("TADO_MODE")
    raw["overlay"]["termination"]["projectedExpiry"] = "2026-09-06T00:00:00+02:00"
    assert snapshot.normalize(raw)["expires_at"] == snapshot.timestamp("2026-09-05T22:00:00Z")


def test_timer_off(snapshot):
    result = snapshot.normalize(zone("TIMER", power="OFF", expiry="2020-01-01T00:00:00Z"))
    assert result["mode"] == "off" and result["expires_at"] == 1577836800


@pytest.mark.parametrize("kind", ["TIMER", "TADO_MODE", "NEXT_TIME_BLOCK", "NEW", [], {}])
def test_unknown_or_missing_deadline_rejected(snapshot, kind):
    with pytest.raises(snapshot.SnapshotError):
        snapshot.normalize(zone(kind))


@pytest.mark.parametrize("value", [None, 3600, "2026-01-01T12:00:00", "tomorrow", ""])
def test_invalid_expiry(snapshot, value):
    with pytest.raises(snapshot.SnapshotError):
        snapshot.timestamp(value)


@pytest.mark.parametrize(
    "raw",
    [
        None,
        {},
        {"setting": None},
        {"setting": []},
        {"setting": {"type": "HEATING"}},
        {"setting": {"type": "HEATING"}, "overlay": []},
        {"setting": {"type": "AIR_CONDITIONING"}, "overlay": None},
    ],
)
def test_invalid_zone(snapshot, raw):
    with pytest.raises(snapshot.SnapshotError):
        snapshot.normalize(raw)


@pytest.mark.parametrize("value", [None, True, "21", float("nan"), float("inf"), [], {}])
def test_invalid_temperature(snapshot, value):
    with pytest.raises(snapshot.SnapshotError):
        snapshot.normalize(zone(temperature=value))


def test_partial_failure_and_filtering(snapshot):
    response = {"zoneStates": {"1": zone(), "2": zone("TIMER"), "3": zone()}}
    result = snapshot.normalize_response(response, [1, 2, 99, 1])
    assert set(result["snapshots"]) == {"1"}
    assert result["errors"] == {"2": "missing_expiry", "99": "invalid_zone"}
    assert "do-not-export" not in json.dumps(result)


def test_all_zones(snapshot):
    assert set(
        snapshot.normalize_response({"zoneStates": {"2": zone(), "1": zone()}}, None)["snapshots"]
    ) == {"1", "2"}


@pytest.mark.parametrize(
    "response", [None, {}, {"zoneStates": []}, {"zoneStates": {}}, {"zoneStates": {"invalid": {}}}]
)
def test_invalid_response(snapshot, response):
    with pytest.raises(snapshot.SnapshotError):
        snapshot.normalize_response(response, None)
