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
    "brandLogo", "pilotMap", "fitCaliforniaBtn", "myAreaBtn", "refreshMapBtn",
    "mapPilotList", "mapRosterMeta", "mapSelectionText", "clearSelectionBtn",
    "gpsBtn", "gpsStatus", "snapshotDot", "snapshotText", "pilotFilterText",
    "pilotSearch", "refreshPilotsBtn", "pilotList", "targetCoords",
    "appleTarget", "googleTarget", "w3wTarget", "copyTargetBtn",
]:
    assert required_id in parser.ids, f"Missing UI control: {required_id}"

for needle in [
    "id=\"brandLogo\"",
    "class=\"brandLogo\"",
    "src=\"./assets/brand-logo.svg\"",
    "alt=\"Sky Finder — Paraglider Rescue Locator\"",
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
    "syncSelectionToMapView",
    "Questions/Suggestions",
    "mailto:Sky.Bonillo@gmail.com",
    "gpsActions",
    "assets/brand-logo.svg",
    "navigationCard",
    "pilotMarkerIcon",
    "setPilotAsTarget",
    "w3wModal",
    "w3wFrame",
    "w3wCoordinateUrl",
    "geolocation 'none'",
]:
    assert needle in html, f"Missing required behavior: {needle}"

sw = (ROOT / "sw.js").read_text()
assert "sky-finder-v1.4.15" in sw
assert "request.mode === 'navigate'" in sw
assert "url.origin !== self.location.origin" in sw

scripts = re.findall(r"<script(?:\s[^>]*)?>(.*?)</script>", html, flags=re.S | re.I)
inline_scripts = [s for s in scripts if s.strip()]
assert inline_scripts, "No inline application script found"
app_script = "\n".join(inline_scripts)

with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False) as tmp:
    tmp.write(app_script)
    tmp_path = tmp.name
subprocess.run(["node", "--check", tmp_path], check=True)
subprocess.run(["node", "--check", str(ROOT / "sw.js")], check=True)
subprocess.run(["python", str(ROOT / "scripts" / "test_live_snapshot.py")], check=True)

# Execute the exact rescue math and coordinate parser extracted from index.html.
# This catches calculation regressions rather than only checking that function
# names remain present in the source.
runtime_test = f"""
'use strict';
const source = {json.dumps(app_script)};
const start = source.indexOf('function parseCoordinates(raw)');
const end = source.indexOf('function setTargetLinks');
if (start < 0 || end <= start) throw new Error('Unable to extract rescue math functions');
const extracted = new Function(source.slice(start, end) +
  '; return {{parseCoordinates, haversineMiles, bearingDegrees, cardinal}};')();
const {{parseCoordinates, haversineMiles, bearingDegrees, cardinal}} = extracted;
const assert = (condition, message) => {{ if (!condition) throw new Error(message); }};
const near = (actual, expected, tolerance, message) =>
  assert(Math.abs(actual - expected) <= tolerance, `${{message}}: ${{actual}}`);

let point = parseCoordinates('34.4208, -119.6982');
assert(point && point.lat === 34.4208 && point.lng === -119.6982, 'decimal coordinates failed');
point = parseCoordinates('lat: 34.4208, longitude: -119.6982');
assert(point && point.lat === 34.4208 && point.lng === -119.6982, 'labeled coordinates failed');
assert(parseCoordinates('91, -119') === null, 'invalid latitude accepted');
assert(parseCoordinates('34, -181') === null, 'invalid longitude accepted');
assert(parseCoordinates('not coordinates') === null, 'invalid text accepted');

near(haversineMiles({{lat:0,lng:0}}, {{lat:0,lng:1}}), 69.093, 0.05, 'distance calculation failed');
near(haversineMiles({{lat:34.4208,lng:-119.6982}}, {{lat:34.4208,lng:-119.6982}}), 0, 1e-9, 'zero distance failed');
near(bearingDegrees({{lat:0,lng:0}}, {{lat:0,lng:1}}), 90, 0.01, 'east bearing failed');
near(bearingDegrees({{lat:0,lng:0}}, {{lat:1,lng:0}}), 0, 0.01, 'north bearing failed');
assert(cardinal(90) === 'E', 'east cardinal failed');
assert(cardinal(225) === 'SW', 'southwest cardinal failed');
console.log('Sky Finder rescue math runtime tests: PASS');
"""
with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False) as tmp:
    tmp.write(runtime_test)
    runtime_test_path = tmp.name
subprocess.run(["node", runtime_test_path], check=True)

assert "https://what3words.com/?map=" not in html, "Broken legacy what3words map handoff remains"
assert "https://map.what3words.com/${p.lat},${p.lng}" not in html, "Unreliable top-level coordinate-path W3W handoff remains"
assert "dataset.safeCopy" not in html, "Obsolete W3W copy/paste fallback remains"
assert "W3W Copy" not in html, "Obsolete W3W copy button remains"
assert "function w3wCoordinateUrl(p)" in html, "Embedded W3W coordinate URL builder missing"
assert "allow=\"geolocation 'none'; fullscreen\"" in html, "Embedded W3W must not receive responder geolocation"
assert "els.w3wFrame.src=w3wCoordinateUrl(p)" in html, "W3W modal must use selected pilot coordinates"
assert "els.w3wFrame.src='about:blank'" in html, "W3W modal must unload on close"
assert "map.on('moveend zoomend',()=>{syncSelectionToMapView();renderMapRoster();renderPilots();updateFilterText()})" in html, "Map movement must sync both pilot lists"
assert "return visiblePilots().filter(p=>selectedPilotIds.has(pilotId(p))).sort(pilotSort)" in html, "Selected rescue list must remain inside map bounds"
print("Sky Finder static validation: PASS")

# UI-only redesign guardrails
assert 'class="card mapCard"' in html
assert 'class="card navigationCard"' in html
assert html.index('class="card mapCard"') < html.index('class="card navigationCard"') < html.index('class="card toolsCard"')
assert 'Pilot Area Map' not in html, 'Redundant Pilot Area Map label remains'
assert 'Verify timestamp in XCFind.' not in html, 'Redundant timestamp instruction remains'
assert 'L.marker([Number(p.lat),Number(p.lng)]' in html, 'Paraglider map marker implementation missing'
assert 'pilotParaglider' in html and 'pgCanopy' in html, 'Paraglider marker visual missing'
assert 'minmax(390px,56vh)' in html, 'Mobile map minimum height guard missing'
assert './assets/brand-logo.svg' in html, 'Approved brand logo missing from header'

assert '>XCFind Tracks<' not in html, 'XCFind Tracks map tab must remain removed'
assert '>Verify XCFind<' not in html, 'Verify XCFind must remain removed from pilot cards'
assert '>what3words</button>' in html, 'what3words button must be spelled out'
assert html.index('class="targetLinks"') < html.index('id="metrics"'), 'Distance/bearing must remain below navigation buttons'
assert "if(!myPosition&&watchId===null)startGps(false)" in html, 'Pilot selection must auto-start responder GPS when needed'
assert "els.distanceValue.textContent='Locating…'" in html, 'Metric cards must show GPS acquisition state'
assert '/* Sky Finder dark field theme' in html, 'Dark field theme missing'
assert "'./assets/brand-logo.svg'" in sw, 'Approved brand logo missing from service-worker shell'
print('Sky Finder UI redesign checks: PASS')


# Pilot status legend guardrails
assert 'id="pilotStatusLegend"' in html, 'Pilot status legend missing'
legend_start = html.index('id="pilotStatusLegend"')
legend_end = html.index('      </section>', legend_start)
legend_html = html[legend_start:legend_end]
for text in [
    'HELP REQUEST', 'Pilot/device requesting help',
    'RECENT TRACK POINT', 'Last track point within 2 hrs',
    'AGING TRACK POINT', 'Last track point 2–12 hrs old',
    'STALE TRACK POINT', 'Last track point over 12 hrs old',
]:
    assert text in legend_html, f'Missing legend text: {text}'
assert legend_html.index('HELP REQUEST') < legend_html.index('RECENT TRACK POINT') < legend_html.index('AGING TRACK POINT') < legend_html.index('STALE TRACK POINT'), 'Legend order must be HELP, recent, aging, stale'
assert legend_html.count('class="legendPg"') == 4, 'Legend must use four paraglider icons'
assert 'legendCanopy' in legend_html and 'legendLines' in legend_html and 'legendPilot' in legend_html, 'Legend paraglider silhouette incomplete'
assert 'map-pin' not in legend_html.lower(), 'Legend must not contain a map-pin/V shape'
print('Sky Finder pilot status legend checks: PASS')
