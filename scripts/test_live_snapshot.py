#!/usr/bin/env python3
from __future__ import annotations

from build_live_snapshot import METERS_TO_FEET, transform_feed


def test_latest_timestamp_wins_and_output_is_minimal() -> None:
    fixture = {
        "devices": [
            {
                "DeviceID": "secret-device-1",
                "PilotID": "2765",
                "Name": "Test&nbsp;Pilot",
                "Messages": [
                    {"Timestamp": "200", "Type": "1", "Lat": "34.5", "Lng": "-119.7", "Alt": "1000", "MsgText": "do not publish", "Battery": "99"},
                    {"Timestamp": "100", "Type": "0", "Lat": "34.4", "Lng": "-119.6", "Alt": "900", "MsgText": "older"},
                ],
            },
            {
                "DeviceID": "bad-coordinate",
                "PilotID": "2",
                "Name": "Invalid",
                "Messages": [{"Timestamp": "300", "Type": "0", "Lat": "134", "Lng": "-119", "Alt": "10"}],
            },
        ],
        "telegrams": [],
    }
    snapshot = transform_feed(fixture, fetched_at_epoch=1_000)
    assert snapshot["pilot_count"] == 1
    assert snapshot["fetched_at"] == "1970-01-01T00:16:40Z"
    pilot = snapshot["pilots"][0]
    assert pilot["name"] == "Test Pilot"
    assert pilot["timestamp"] == 200
    assert pilot["lat"] == 34.5
    assert pilot["lng"] == -119.7
    assert pilot["type"] == "1"
    assert pilot["alt_ft"] == round(1000 * METERS_TO_FEET)
    assert set(pilot) == {"name", "pilot_id", "timestamp", "lat", "lng", "type", "alt_ft"}
    serialized = repr(snapshot)
    assert "do not publish" not in serialized
    assert "secret-device-1" not in serialized
    assert "Battery" not in serialized
    assert "&nbsp;" not in serialized


def test_invalid_structure_fails() -> None:
    try:
        transform_feed({"no_devices": []}, fetched_at_epoch=1_000)
    except ValueError:
        return
    raise AssertionError("invalid XCFind feed should raise ValueError")


if __name__ == "__main__":
    test_latest_timestamp_wins_and_output_is_minimal()
    test_invalid_structure_fails()
    print("Sky Finder live snapshot unit tests: PASS")
