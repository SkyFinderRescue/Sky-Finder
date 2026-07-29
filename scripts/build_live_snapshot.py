#!/usr/bin/env python3
"""Build a minimal Sky Finder latest-position snapshot from XCFind's public feed.

The published snapshot intentionally contains only the fields needed to find and
route to a pilot's last known point. It does not republish message text, battery
state, device IDs, or track history.
"""
from __future__ import annotations

import argparse
import html
import json
import math
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

GROUP_ID = 16
DATE_RANGE = 2  # XCFind map.js defines 2 as 48 hours.
SOURCE_URL = f"https://xcfind.paraglide.us/map.html?id={GROUP_ID}"
SOURCE_ENDPOINT = (
    f"https://xcfind.paraglide.us/getmessagesjson.php?groupId={GROUP_ID}"
    f"&dateRange={DATE_RANGE}"
)
USER_AGENT = "SkyFinderRescue/1.1 (+https://github.com/SkyFinderRescue/Sky-Finder)"
METERS_TO_FEET = 3.280839895013123


def _finite_float(value: Any) -> float | None:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if math.isfinite(result) else None


def _timestamp(value: Any) -> int | None:
    number = _finite_float(value)
    if number is None or number <= 0:
        return None
    return int(number)


def _latest_message(messages: Any) -> dict[str, Any] | None:
    if not isinstance(messages, list):
        return None
    candidates: list[tuple[int, dict[str, Any]]] = []
    for message in messages:
        if not isinstance(message, dict):
            continue
        ts = _timestamp(message.get("Timestamp"))
        if ts is not None:
            candidates.append((ts, message))
    if not candidates:
        return None
    return max(candidates, key=lambda item: item[0])[1]


def _pilot_name(value: Any) -> str:
    decoded = html.unescape(str(value or "Unnamed pilot")).replace("\u00a0", " ")
    cleaned = " ".join(decoded.split())
    return cleaned or "Unnamed pilot"


def transform_feed(data: Any, fetched_at_epoch: int | None = None) -> dict[str, Any]:
    if not isinstance(data, dict) or not isinstance(data.get("devices"), list):
        raise ValueError("XCFind response is missing the devices list")

    now = int(time.time()) if fetched_at_epoch is None else int(fetched_at_epoch)
    pilots: list[dict[str, Any]] = []

    for device in data["devices"]:
        if not isinstance(device, dict):
            continue
        latest = _latest_message(device.get("Messages"))
        if latest is None:
            continue

        lat = _finite_float(latest.get("Lat"))
        lng = _finite_float(latest.get("Lng"))
        ts = _timestamp(latest.get("Timestamp"))
        if lat is None or lng is None or ts is None:
            continue
        if not (-90 <= lat <= 90 and -180 <= lng <= 180):
            continue

        name = _pilot_name(device.get("Name"))
        pilot_id = str(device.get("PilotID") or "").strip()
        msg_type = str(latest.get("Type") or "").strip()
        alt_m = _finite_float(latest.get("Alt"))

        pilot: dict[str, Any] = {
            "name": name,
            "pilot_id": pilot_id,
            "timestamp": ts,
            "lat": round(lat, 6),
            "lng": round(lng, 6),
            "type": msg_type,
            "alt_ft": round(alt_m * METERS_TO_FEET) if alt_m is not None and alt_m != 0 else None,
        }
        pilots.append(pilot)

    pilots.sort(key=lambda p: (-int(p["timestamp"]), str(p["name"]).casefold()))
    fetched_at = datetime.fromtimestamp(now, tz=timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")

    return {
        "schema_version": 1,
        "source": "XCFind",
        "source_url": SOURCE_URL,
        "source_endpoint": SOURCE_ENDPOINT,
        "group_id": GROUP_ID,
        "window_hours": 48,
        "fetched_at": fetched_at,
        "fetched_at_epoch": now,
        "pilot_count": len(pilots),
        "pilots": pilots,
    }


def fetch_feed(timeout: int = 25) -> dict[str, Any]:
    request = urllib.request.Request(
        SOURCE_ENDPOINT,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "application/json",
            "Cache-Control": "no-cache",
        },
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        if response.status != 200:
            raise RuntimeError(f"XCFind returned HTTP {response.status}")
        content_type = (response.headers.get("Content-Type") or "").lower()
        if "json" not in content_type:
            raise RuntimeError(f"XCFind returned unexpected content type: {content_type}")
        body = response.read().decode("utf-8")
    data = json.loads(body)
    if not isinstance(data, dict):
        raise RuntimeError("XCFind response was not a JSON object")
    return data


def build(output_path: Path) -> dict[str, Any]:
    snapshot = transform_feed(fetch_feed())
    if snapshot["pilot_count"] < 1:
        raise RuntimeError("XCFind snapshot contained no valid latest pilot positions")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(snapshot, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return snapshot


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("output", nargs="?", default="latest.json")
    args = parser.parse_args()
    snapshot = build(Path(args.output))
    print(f"Sky Finder live snapshot: {snapshot['pilot_count']} pilots; fetched {snapshot['fetched_at']}")


if __name__ == "__main__":
    main()
