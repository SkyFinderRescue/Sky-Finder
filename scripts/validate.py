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
    "xcframe", "reloadMapBtn", "gpsBtn", "gpsStatus", "targetCoords",
    "appleTarget", "googleTarget", "w3wTarget", "copyTargetBtn",
]:
    assert required_id in parser.ids, f"Missing UI control: {required_id}"

for needle in [
    "navigator.geolocation.watchPosition",
    "els.gpsBtn.addEventListener('click', startGps)",
    "haversineMiles",
    "bearingDegrees",
    "https://xcfind.paraglide.us/map.html?id=16",
]:
    assert needle in html, f"Missing required behavior: {needle}"

scripts = re.findall(r"<script(?:\s[^>]*)?>(.*?)</script>", html, flags=re.S | re.I)
assert scripts, "No inline application script found"
with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False) as tmp:
    tmp.write("\n".join(scripts))
    tmp_path = tmp.name
subprocess.run(["node", "--check", tmp_path], check=True)
subprocess.run(["node", "--check", str(ROOT / "sw.js")], check=True)

print("Sky Finder static validation: PASS")
