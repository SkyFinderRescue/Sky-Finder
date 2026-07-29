from __future__ import annotations

import json
import re
import subprocess
import tempfile
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

required = [
    ROOT / "index.html",
    ROOT / "manifest.webmanifest",
    ROOT / "sw.js",
    ROOT / "assets" / "icon.svg",
    ROOT / "scripts" / "build_live_snapshot.py",
    ROOT / "scripts" / "test_live_snapshot.py",
    ROOT / ".github" / "workflows" / "update-live-data.yml",
]
for path in required:
    assert path.exists(), f"Missing required file: {path.relative_to(ROOT)}"

manifest = json.loads((ROOT / "manifest.webmanifest").read_text())
assert manifest["name"] == "Sky Finder"
assert manifest["display"] == "standalone"
for icon in manifest.get("icons", []):
    assert (ROOT / icon["src"]).exists(), f"Missing manifest icon: {icon['src']}"

class IdParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids: list[str] = []

    def handle_starttag(self, tag, attrs):
        for key, value in attrs:
            if key == "id" and value:
                self.ids.append(value)

html = (ROOT / "index.html").read_text()
parser = IdParser()
parser.feed(html)
assert len(parser.ids) == len(set(parser.ids)), "Duplicate HTML ids detected"
for required_id in [
    "pilotMap", "fitCaliforniaBtn", "myAreaBtn", "refreshMapBtn",
    "mapPilotList", "mapRosterMeta", "mapSelectionText", "clearSelectionBtn",
    "gpsBtn", "gpsStatus", "snapshotDot", "snapshotText", "pilotFilterText",
    "pilotSearch", "refreshPilotsBtn", "pilotList", "targetCoords",
    "appleTarget", "googleTarget", "w3wTarget", "copyTargetBtn",
]:
    assert required_id in parser.ids, f"Missing UI control: {required_id}"

for needle in [
    "navigator.geolocation.watchPosition",
    "haversineMiles",
    "bearingDegrees",
    "https://xcfind.paraglide.us/map.html?id=16",
    "SNAPSHOT_URL",
    "loadPilotSnapshot",
    "L.map('pilotMap'",
    "visiblePilots",
    "map.getBounds()",
    "selectedPilotIds",
    "togglePilotSelection",
    "Use Last Point",
    "Verify XCFind",
    "XCFind Tracks",
    "Questions/Suggestions",
    "mailto:Sky.Bonillo@gmail.com",
    "Pilot Area Map",
    "gpsActions",
    "setPilotAsTarget",
    "https://map.what3words.com/",
    "Copied for what3words",
]:
    assert needle in html, f"Missing required behavior: {needle}"

sw = (ROOT / "sw.js").read_text()
assert "sky-finder-v1.4.0" in sw
assert "request.mode === 'navigate'" in sw
assert "url.origin !== self.location.origin" in sw

scripts = re.findall(r"<script(?:\s[^>]*)?>(.*?)</script>", html, flags=re.S | re.I)
inline_scripts = [s for s in scripts if s.strip()]
assert inline_scripts, "No inline application script found"
with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False) as tmp:
    tmp.write("\n".join(inline_scripts))
    tmp_path = tmp.name
subprocess.run(["node", "--check", tmp_path], check=True)
subprocess.run(["node", "--check", str(ROOT / "sw.js")], check=True)
subprocess.run(["python", str(ROOT / "scripts" / "test_live_snapshot.py")], check=True)

print("Sky Finder static validation: PASS")

assert "https://what3words.com/?map=" not in html, "Unsafe legacy what3words coordinate URL is still present"
