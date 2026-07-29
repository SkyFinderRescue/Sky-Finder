from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "index.html"
SW = ROOT / "sw.js"
VALIDATE = ROOT / "scripts" / "validate.py"

html = INDEX.read_text()


def replace_once(old: str, new: str) -> None:
    global html
    count = html.count(old)
    if count != 1:
        raise RuntimeError(f"Expected exactly one match, found {count}: {old[:100]!r}")
    html = html.replace(old, new, 1)


compact_css = r'''    /* Compact field layout */
    .gpsActions{display:grid;grid-template-columns:1.3fr .75fr .75fr;gap:7px}.footer{display:flex;flex-wrap:wrap;justify-content:center;gap:4px 12px}.footer a{color:#cbd8ee;text-decoration:none}.srOnly{position:absolute!important;width:1px;height:1px;padding:0;margin:-1px;overflow:hidden;clip:rect(0,0,0,0);white-space:nowrap;border:0}
    @media(max-width:650px){.app{padding:8px}.topbar{margin-bottom:8px;gap:8px;align-items:center}.brand h1{font-size:23px}.brand p{font-size:11px;margin-top:2px;line-height:1.2}.live{font-size:10px;padding:5px 8px;gap:5px}.dot{width:7px;height:7px}.card{border-radius:15px}.cardHead{padding:9px 10px;gap:6px}.cardHead h2{font-size:15px}.cardHead .actions{gap:5px}.cardHead .actions .btn{min-height:34px;padding:6px 8px;font-size:11px}.mapStage{grid-template-rows:110px minmax(285px,1fr);height:49vh;min-height:410px}.mapRosterHead{padding:7px 8px 6px}.mapRosterTitle{font-size:10px}.mapRosterMeta{font-size:9px;margin-top:2px}.mapPilotList{padding:5px;gap:3px}.mapPilotRow{padding:4px 6px;gap:6px}.mapPilotRow input{width:15px;height:15px}.mapPilotName{font-size:11px}.mapPilotMeta{font-size:9px}.mapSelection{left:7px;top:7px;padding:5px 7px;font-size:9px;max-width:calc(100% - 14px)}.mapOverlay{right:7px;bottom:7px;gap:5px}.mapOverlay .btn{min-height:34px;padding:7px 9px;font-size:11px}.cardBody{padding:9px 10px}.note{padding:7px 8px;font-size:10px;line-height:1.35}.section + .section{margin-top:10px;padding-top:10px}.section h3{font-size:14px;margin-bottom:6px}.gpsActions .btn{min-height:40px;padding:8px 6px;font-size:12px}.status{margin-top:6px;padding:7px 9px;font-size:11px;line-height:1.35}.snapshotLine{margin-top:5px;font-size:10px}.filterLine{margin-top:4px;font-size:10px}input[type="text"],input[type="search"]{min-height:42px;padding:9px 10px;font-size:14px}.pilotSearchRow{gap:6px}.pilotSearchRow .btn{min-height:42px;padding:8px 10px;font-size:12px}.pilotList{max-height:245px;gap:6px;margin-top:7px}.pilotCard{padding:8px}.pilotName{font-size:14px}.pilotMeta,.pilotCoords{font-size:10px;margin-top:3px}.pilotActions{grid-template-columns:1.1fr .9fr;gap:5px;margin-top:6px}.pilotActions .btn{min-height:36px;padding:7px 6px;font-size:11px}.pilotMinorActions{margin-top:5px}.pilotMinorActions .btn{min-height:32px;padding:6px;font-size:10px}.label{margin:8px 0 4px;font-size:10px}.metricGrid{gap:6px;margin-top:7px}.metric{padding:8px}.metric .k{font-size:9px}.metric .v{font-size:17px;margin-top:3px}.targetLinks{grid-template-columns:1fr 1fr;gap:6px;margin-top:7px}.targetLinks .btn{min-height:38px;padding:7px 6px;font-size:12px}.footer{padding:9px 4px 14px;font-size:10px;line-height:1.35;gap:2px 10px}}
    @media(max-width:470px){.pilotActions{grid-template-columns:1fr 1fr}.targetLinks{grid-template-columns:1fr 1fr}}
'''
replace_once("  </style>", compact_css + "  </style>")

replacements = {
    '<p>California paraglider rescue locator</p>': '<p>Paraglider rescue locator</p>',
    '<span id="liveText">Pilot map loading</span>': '<span id="liveText">Loading</span>',
    '<h2 id="pilotMapTitle">Recent Pilot Area Map</h2>': '<h2 id="pilotMapTitle">Pilot Area Map</h2>',
    '>Fit California</button>': '>California</button>',
    '>Refresh Data</button>': '>Refresh</button>',
    '<div class="mapRosterTitle">Pilots in map view</div>': '<div class="mapRosterTitle">Pilots in View</div>',
    '<strong>Area mode:</strong> zoom or pan to the incident area. The pilot lists follow the visible map.': '<strong>Area mode:</strong> zoom/pan to incident area.',
    '>Clear Selected</button>': '>Clear</button>',
    '>Open XCFind Tracks</a>': '>XCFind Tracks</a>',
    '<div class="cardBody"><div class="note"><strong>Field use:</strong> zoom/pan to the reported area to see recent pilot last-points there. Check one or more pilot names on the left (or tap their map markers) and Rescue Tools will show only those selected pilots. Point age is always shown; verify the pilot and timestamp in XCFind before committing resources.</div></div>': '<div class="cardBody"><div class="note"><strong>Field use:</strong> Tap a pilot or marker to select. Verify timestamp in XCFind.</div></div>',
    '<section class="section"><h3>Responder location</h3><div class="actions"><button id="gpsBtn" class="btn primary" type="button">Use My GPS</button><button id="copyMyBtn" class="btn" type="button" disabled>Copy</button><button id="shareMyBtn" class="btn" type="button" disabled>Share</button></div>': '<section class="section"><h3>Responder GPS</h3><div class="actions gpsActions"><button id="gpsBtn" class="btn primary" type="button">Use GPS</button><button id="copyMyBtn" class="btn" type="button" disabled>Copy</button><button id="shareMyBtn" class="btn" type="button" disabled>Share</button></div>',
    '<section class="section"><h3>Find pilot</h3><p class="small">No pilot name? Zoom the map to the reported area and this list shows pilots in that view. Select a name/marker and the list switches to selected pilots only. You can also search the full recent XCFind snapshot by name.</p>': '<section class="section"><h3>Find pilot</h3><p class="small">Zoom to the incident area or search by name.</p>',
    '<label class="label" for="pilotSearch">Pilot name</label>': '<label class="label srOnly" for="pilotSearch">Pilot name</label>',
    '<section class="section"><h3>Pilot / incident location</h3><p class="small">Choose <strong>Use Last Point</strong> for a pilot or paste verified coordinates here for navigation and distance/bearing from your current location.</p><label class="label" for="targetCoords">Coordinates</label>': '<section class="section"><h3>Navigation</h3><label class="label srOnly" for="targetCoords">Coordinates</label>',
    '>Copy Target</button>': '>Copy</button>',
    '<section class="section"><h3>Operational fallback</h3><p class="small">If the area map or snapshot is unavailable, use <strong>Open XCFind Tracks</strong> for the source map. Routing tools and manual coordinate entry continue to work independently.</p></section>': '',
    '<div class="footer">Sky Finder is a rescue aid. XCFind remains the source of pilot tracking data; verify pilot identity, timestamp, and coordinates before committing resources.</div>': '<div class="footer"><span>Verify pilot + timestamp in XCFind.</span><span>Questions/Suggestions: <a href="mailto:Sky.Bonillo@gmail.com">Sky.Bonillo@gmail.com</a></span></div>',
    "setMapState('Area map ready',true)": "setMapState('Map ready',true)",
    "els.mapSelectionText.innerHTML=`<strong>Selected ${names.length}:</strong> ${escapeHtml(names.join(', '))}. Rescue Tools is filtered to selected pilots only.`": "els.mapSelectionText.innerHTML=`<strong>Selected:</strong> ${escapeHtml(names.join(', '))}`",
    "else els.mapSelectionText.innerHTML='<strong>Area mode:</strong> zoom or pan to the incident area. The pilot lists follow the visible map.'": "else els.mapSelectionText.innerHTML='<strong>Area mode:</strong> zoom/pan to incident area.'",
    "els.mapRosterMeta.textContent=`${pilots.length} recent last-point${pilots.length===1?'':'s'} in view${selectedCount?` • ${selectedCount} selected`:''}`": "els.mapRosterMeta.textContent=`${pilots.length} in view${selectedCount?` • ${selectedCount} selected`:''}`",
    "els.pilotFilterText.textContent=`${selectedPilotIds.size} selected pilot${selectedPilotIds.size===1?'':'s'} — other names hidden.`": "els.pilotFilterText.textContent=`${selectedPilotIds.size} selected.`",
    "els.pilotFilterText.textContent=`${count} search match${count===1?'':'es'} across the recent XCFind snapshot.`": "els.pilotFilterText.textContent=`${count} search match${count===1?'':'es'}.`",
    "els.pilotFilterText.textContent=`${count} recent pilot last-point${count===1?'':'s'} inside the visible map area.`": "els.pilotFilterText.textContent=`${count} in map view.`",
    "<a class=\"btn verifyPilotBtn\" href=\"${pilotDetailUrl(p)}\" target=\"_blank\" rel=\"noopener noreferrer\">Verify in XCFind</a>": "<a class=\"btn verifyPilotBtn\" href=\"${pilotDetailUrl(p)}\" target=\"_blank\" rel=\"noopener noreferrer\">Verify XCFind</a>",
    "<div class=\"pilotMinorActions\"><button class=\"btn focusPilotBtn\" type=\"button\" data-pilot-id=\"${escapeHtml(id)}\">Show + Select</button>${selected?`<button class=\"btn deselectPilotBtn\" type=\"button\" data-pilot-id=\"${escapeHtml(id)}\">Remove Selection</button>`:''}</div>": "<div class=\"pilotMinorActions\">${selected?`<button class=\"btn deselectPilotBtn\" type=\"button\" data-pilot-id=\"${escapeHtml(id)}\">Remove</button>`:`<button class=\"btn focusPilotBtn\" type=\"button\" data-pilot-id=\"${escapeHtml(id)}\">Select</button>`}</div>",
    "setSnapshotStatus(`${data.pilots.length} recent pilots • ${age.text} • ${windowHours}h source window`,age.cls)": "setSnapshotStatus(`${data.pilots.length} pilots • ${age.text} • ${windowHours}h window`,age.cls)",
    "setMapState(age.cls==='bad'?'Pilot data stale — verify XCFind':'Pilot map + snapshot ready',age.cls!=='bad')": "setMapState(age.cls==='bad'?'Data stale':'Ready',age.cls!=='bad')",
    "setMapState(map?'Map ready • pilot snapshot unavailable':'Map unavailable — use XCFind',false)": "setMapState(map?'Map only':'Unavailable',false)",
}

for old, new in replacements.items():
    replace_once(old, new)

INDEX.write_text(html)

sw = SW.read_text()
if sw.count("sky-finder-v1.2.0") != 1:
    raise RuntimeError("Unexpected service worker version")
SW.write_text(sw.replace("sky-finder-v1.2.0", "sky-finder-v1.3.0", 1))

validate = VALIDATE.read_text()
if validate.count('assert "sky-finder-v1.2.0" in sw') != 1:
    raise RuntimeError("Unexpected validator service-worker assertion")
validate = validate.replace('assert "sky-finder-v1.2.0" in sw', 'assert "sky-finder-v1.3.0" in sw', 1)
anchor = '    "Open XCFind Tracks",\n'
if anchor not in validate:
    raise RuntimeError("Validator needle anchor missing")
validate = validate.replace(anchor, '    "XCFind Tracks",\n    "mailto:Sky.Bonillo@gmail.com",\n    "Questions/Suggestions",\n', 1)
VALIDATE.write_text(validate)

print("Compact mobile UI patch applied")
